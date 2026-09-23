"""Browser-backed website collection regression tests.

The local fixture is reached only through monkeypatched dependencies in this test;
production URL validation and Playwright network guarding are never relaxed.
"""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.audit.workspace import AuditWorkspace
from src.security.network_policy import UnsafeURLError, ValidatedURL, validate_public_url
import src.main as website_main
from src.jobs import AuditWorker
from src.ui import server
from test_server_security import api_server, request


class FixtureSite(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path == "/broken":
            # A deterministic transport failure: collection must preserve the
            # other pages rather than converting this run to all-pass/all-fail.
            self.connection.close()
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/about")
            self.end_headers()
            return
        pages = {
            "/": """<main><h1>Fixture home</h1><nav><a href='/about'>About</a><a href='/spa'>SPA</a></nav><button id='bad'></button><form><label>Email <input type='email'></label><button>Send</button></form></main>""",
            "/about": "<main><h1>About fixture</h1><p>Representative content.</p></main>",
            "/spa": "<main><h1>Loading</h1><script>setTimeout(()=>document.querySelector('h1').textContent='Rendered SPA content', 20)</script></main>",
            "/alpha": "<main><h1>AUDIT_FIXTURE_ALPHA</h1><button id='alpha-unnamed'></button></main>",
            "/bravo": "<main><h1>AUDIT_FIXTURE_BRAVO</h1><input id='bravo-unlabeled'></main>",
        }
        body = pages.get(self.path)
        if body is None:
            self.send_error(404)
            return
        encoded = ("<!doctype html><html><body>" + body + "</body></html>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


@pytest.fixture
def fixture_site():
    instance = ThreadingHTTPServer(("127.0.0.1", 0), FixtureSite)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{instance.server_port}"
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=3)


def test_production_ssrf_policy_still_rejects_localhost():
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://127.0.0.1/")


def test_browser_collection_captures_multi_page_spa_and_axe_evidence(tmp_path, monkeypatch, fixture_site):
    pytest.importorskip("playwright.async_api")
    workspace = AuditWorkspace("browser-e2e", tmp_path / "audits")
    workspace.prepare(mode="website")
    pages = [
        {"name": "Home", "url": f"{fixture_site}/"},
        {"name": "About", "url": f"{fixture_site}/about"},
        {"name": "SPA", "url": f"{fixture_site}/spa"},
        {"name": "Broken", "url": f"{fixture_site}/broken"},
    ]
    workspace.website_menu.write_text(json.dumps({"homepage": f"{fixture_site}/", "navigation": pages}), encoding="utf-8")

    checked = lambda url: ValidatedURL(url=url, hostname="fixture.test", port=80, addresses=("127.0.0.1",))
    monkeypatch.setattr(website_main.AuditWorkspace, "for_repository", classmethod(lambda _cls, _job_id: workspace))
    monkeypatch.setattr(website_main, "validate_public_url", checked)
    monkeypatch.setattr(website_main, "install_playwright_network_guard", lambda *_args: asyncio.sleep(0))
    monkeypatch.setattr(website_main, "chromium_host_resolver_rules", lambda _urls: "")
    monkeypatch.setattr(website_main, "run_lighthouse", lambda **_kwargs: {"status": "unavailable", "measurement": "not_measured"})
    original_workspace_config = website_main.workspace_config

    def fast_fixture_config(active_workspace):
        config = original_workspace_config(active_workspace)
        config["navigation"].update({"timeoutMs": 2_000, "postLoadDelayMs": 0})
        config["pageReadiness"].update({"networkIdleTimeoutMs": 0, "assetTimeoutMs": 0, "settleDelayMs": 0})
        config["pageCapture"].update({"captureScrollScreenshots": False})
        config["presentationChecks"]["responsiveDesktopMobile"]["enabled"] = False
        return config

    monkeypatch.setattr(website_main, "workspace_config", fast_fixture_config)

    asyncio.run(website_main.async_main("browser-e2e"))

    results = json.loads(workspace.audit_results.read_text(encoding="utf-8"))
    assert results["summary"]["pagesSucceeded"] == 3
    assert results["summary"]["pagesFailed"] == 1
    assert all(page["screenshotPath"] for page in results["pages"] if page["status"] == "success")
    assert "Rendered SPA content" in json.dumps(results)
    home = next(page for page in results["pages"] if page["name"] == "Home")
    assert home["axe"]["status"] == "completed"
    assert any(item["id"] == "button-name" for item in home["axe"]["raw"]["violations"])
    assert all(page["lighthouse"]["measurement"] == "not_measured" for page in results["pages"] if page["status"] == "success")
    coverage = json.loads(workspace.coverage_manifest.read_text(encoding="utf-8"))
    assert coverage["summary"]["coverageStatus"] == "incomplete"
    assert coverage["summary"]["completed"] == 3 and coverage["summary"]["failed"] == 1


def test_concurrent_browser_audits_keep_workspace_and_evidence_isolated(tmp_path, monkeypatch, fixture_site):
    """Two real Chromium collectors must not share workspace/browser artifacts."""
    pytest.importorskip("playwright.async_api")
    workspaces = {name: AuditWorkspace(name, tmp_path / "audits") for name in ("concurrent-alpha", "concurrent-bravo")}
    for name, path, marker in (("concurrent-alpha", "/alpha", "AUDIT_FIXTURE_ALPHA"), ("concurrent-bravo", "/bravo", "AUDIT_FIXTURE_BRAVO")):
        workspace = workspaces[name]
        workspace.prepare(mode="website")
        workspace.website_menu.write_text(json.dumps({"homepage": f"{fixture_site}{path}", "navigation": [{"name": marker, "url": f"{fixture_site}{path}"}]}), encoding="utf-8")

    monkeypatch.setattr(website_main.AuditWorkspace, "for_repository", classmethod(lambda _cls, job_id: workspaces[job_id]))
    monkeypatch.setattr(website_main, "validate_public_url", lambda url: ValidatedURL(url=url, hostname="fixture.test", port=80, addresses=("127.0.0.1",)))
    monkeypatch.setattr(website_main, "install_playwright_network_guard", lambda *_args: asyncio.sleep(0))
    monkeypatch.setattr(website_main, "chromium_host_resolver_rules", lambda _urls: "")
    monkeypatch.setattr(website_main, "run_lighthouse", lambda **_kwargs: {"status": "unavailable", "measurement": "not_measured"})
    original = website_main.workspace_config
    def fast(workspace):
        config = original(workspace)
        config["navigation"].update({"timeoutMs": 2_000, "postLoadDelayMs": 0})
        config["pageReadiness"].update({"networkIdleTimeoutMs": 0, "assetTimeoutMs": 0, "settleDelayMs": 0})
        config["pageCapture"]["captureScrollScreenshots"] = False
        config["presentationChecks"]["responsiveDesktopMobile"]["enabled"] = False
        return config
    monkeypatch.setattr(website_main, "workspace_config", fast)

    async def collect_both():
        await asyncio.gather(website_main.async_main("concurrent-alpha"), website_main.async_main("concurrent-bravo"))
    asyncio.run(collect_both())
    alpha = workspaces["concurrent-alpha"].audit_results.read_text(encoding="utf-8")
    bravo = workspaces["concurrent-bravo"].audit_results.read_text(encoding="utf-8")
    assert "AUDIT_FIXTURE_ALPHA" in alpha and "AUDIT_FIXTURE_BRAVO" not in alpha
    assert "AUDIT_FIXTURE_BRAVO" in bravo and "AUDIT_FIXTURE_ALPHA" not in bravo
    assert workspaces["concurrent-alpha"].page_screenshots != workspaces["concurrent-bravo"].page_screenshots


def test_authenticated_worker_jobs_collect_isolated_sites(api_server, tmp_path, monkeypatch, fixture_site):
    """Join API queueing, durable workers, real collection, and review publication."""
    pytest.importorskip("playwright.async_api")
    created = []
    for suffix, token in (("alpha", "token-a"), ("bravo", "token-b")):
        status, _, body = request(api_server, "POST", "/api/audits", token=token, body={"auditType": "website", "mode": "gtm", "url": f"{fixture_site}/{suffix}"})
        assert status == 202
        created.append(json.loads(body))
    alpha_id, bravo_id = (item["id"] for item in created)
    workspaces = {job_id: AuditWorkspace(job_id, server.AUDITS_DIR) for job_id in (alpha_id, bravo_id)}
    for job_id, suffix, marker in ((alpha_id, "alpha", "AUDIT_FIXTURE_ALPHA"), (bravo_id, "bravo", "AUDIT_FIXTURE_BRAVO")):
        workspace = workspaces[job_id]; workspace.prepare(mode="website")
        workspace.website_menu.write_text(json.dumps({"homepage": f"{fixture_site}/{suffix}", "navigation": [{"name": marker, "url": f"{fixture_site}/{suffix}"}]}), encoding="utf-8")
    monkeypatch.setattr(website_main.AuditWorkspace, "for_repository", classmethod(lambda _cls, job_id: workspaces[job_id]))
    monkeypatch.setattr(website_main, "validate_public_url", lambda url: ValidatedURL(url=url, hostname="fixture.test", port=80, addresses=("127.0.0.1",)))
    monkeypatch.setattr(website_main, "install_playwright_network_guard", lambda *_args: asyncio.sleep(0))
    monkeypatch.setattr(website_main, "chromium_host_resolver_rules", lambda _urls: "")
    monkeypatch.setattr(website_main, "run_lighthouse", lambda **_kwargs: {"status": "unavailable", "measurement": "not_measured"})
    original = website_main.workspace_config
    def fast(workspace):
        config = original(workspace); config["navigation"].update({"timeoutMs": 2_000, "postLoadDelayMs": 0}); config["pageReadiness"].update({"networkIdleTimeoutMs": 0, "assetTimeoutMs": 0, "settleDelayMs": 0}); config["pageCapture"]["captureScrollScreenshots"] = False; config["presentationChecks"]["responsiveDesktopMobile"]["enabled"] = False
        return config
    monkeypatch.setattr(website_main, "workspace_config", fast)
    overlap = threading.Barrier(2); done = threading.Event(); completed = []
    def run_real_collection(job_id):
        overlap.wait(timeout=10)
        asyncio.run(website_main.async_main(job_id))
        Path(workspaces[job_id].report / "index.html").write_text("<html>machine audit</html>", encoding="utf-8")
        completed.append(job_id)
        if len(completed) == 2: done.set()
    monkeypatch.setattr(server, "_run_audit_job", run_real_collection)
    worker = AuditWorker(server.JOB_STORE, server._execute_claimed_job, concurrency=2, poll_seconds=0.01)
    monkeypatch.setattr(server, "JOB_WORKER", worker); worker.start(); worker.notify()
    try:
        assert done.wait(60)
    finally:
        worker.stop()
    alpha, bravo = (server.JOB_STORE.get(job_id) for job_id in (alpha_id, bravo_id))
    assert alpha["status"] == bravo["status"] == "completed"
    alpha_result, bravo_result = (workspaces[job_id].audit_results.read_text(encoding="utf-8") for job_id in (alpha_id, bravo_id))
    assert "AUDIT_FIXTURE_ALPHA" in alpha_result and "AUDIT_FIXTURE_BRAVO" not in alpha_result
    assert "AUDIT_FIXTURE_BRAVO" in bravo_result and "AUDIT_FIXTURE_ALPHA" not in bravo_result
    assert request(api_server, "GET", f"/api/audits/{bravo_id}", token="token-a")[0] == 404
