from __future__ import annotations

import http.client
import json
import threading

import pytest

from src.security.auth import AuthenticationError
from src.audit.workspace import AuditWorkspace
from src.ui import server


@pytest.fixture
def api_server(monkeypatch, tmp_path, user_a, user_b, administrator):
    users = {"token-a": user_a, "token-b": user_b, "token-admin": administrator}

    def authenticate(headers):
        value = headers.get("Authorization", "")
        token = value.removeprefix("Bearer ")
        if token not in users:
            raise AuthenticationError()
        return users[token]

    generated = tmp_path / "generated"
    monkeypatch.setattr(server, "authenticate_bearer", authenticate)
    monkeypatch.setattr(server, "GENERATED_DIR", generated)
    monkeypatch.setattr(server, "OWNERSHIP_DIR", generated / "ownership")
    monkeypatch.setattr(server, "SCREENSHOT_AUDIT_DIR", generated / "screenshot-audits")
    monkeypatch.setattr(server, "GTM_VERCEL_DIR", generated / "vercel-gtm-report")
    monkeypatch.setattr(server, "DETAILED_VERCEL_DIR", generated / "vercel-audit-report")
    monkeypatch.setattr(server, "FIGMA_AUDIT_DIR", generated / "figma-audits")
    monkeypatch.setattr(server, "MOBILE_AUDIT_DIR", generated / "mobile-audits")
    monkeypatch.setattr(server, "_run_audit_job", lambda _job_id: None)
    monkeypatch.setattr(server, "_validate_url", lambda value: value)
    server.RATE_LIMITER.clear()
    with server.JOBS_LOCK:
        server.JOBS.clear()
    instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.AuditRequestHandler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    instance.server_close()
    thread.join(timeout=3)
    with server.JOBS_LOCK:
        server.JOBS.clear()


def request(instance, method, path, *, token=None, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", instance.server_port, timeout=5)
    final_headers = dict(headers or {})
    if token:
        final_headers["Authorization"] = f"Bearer {token}"
    payload = body
    if isinstance(body, dict):
        payload = json.dumps(body).encode()
        final_headers["Content-Type"] = "application/json"
    connection.request(method, path, body=payload, headers=final_headers)
    response = connection.getresponse()
    data = response.read()
    result = (response.status, dict(response.getheaders()), data)
    connection.close()
    return result


def create_audit(instance, token="token-a"):
    status, _headers, body = request(
        instance,
        "POST",
        "/api/audits",
        token=token,
        body={"auditType": "website", "mode": "gtm", "url": "https://example.com/"},
    )
    assert status == 202
    return json.loads(body)


def test_anonymous_invalid_auth_and_unapproved_cors(api_server):
    status, headers, _ = request(api_server, "GET", "/api/criteria", headers={"Origin": "https://evil.test"})
    assert status == 401
    assert "Access-Control-Allow-Origin" not in headers
    assert request(api_server, "GET", "/api/criteria", token="expired")[0] == 401


def test_approved_cors_is_exact_and_security_headers_are_present(api_server):
    status, headers, _ = request(
        api_server,
        "GET",
        "/api/criteria",
        token="token-a",
        headers={"Origin": "http://127.0.0.1:8787"},
    )
    assert status == 200
    assert headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:8787"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_owner_can_create_and_other_user_cannot_read_or_cancel(api_server):
    audit = create_audit(api_server)
    job_id = audit["id"]
    assert "ownerId" not in audit
    assert request(api_server, "GET", f"/api/audits/{job_id}", token="token-a")[0] == 200
    assert request(api_server, "GET", f"/api/audits/{job_id}", token="token-b")[0] == 404
    assert request(api_server, "POST", f"/api/audits/{job_id}/cancel", token="token-b")[0] == 404


def test_admin_has_explicit_criteria_permission_but_no_cross_owner_access(api_server, monkeypatch):
    audit = create_audit(api_server)
    from src.gtm_audit import common

    monkeypatch.setattr(common, "reset_audit_criteria_payload", lambda: {"source": "defaults"})
    assert request(api_server, "POST", "/api/criteria/reset", token="token-a")[0] == 403
    assert request(api_server, "POST", "/api/criteria/reset", token="token-admin")[0] == 200
    assert request(api_server, "GET", f"/api/audits/{audit['id']}", token="token-admin")[0] == 404


def test_raw_html_publication_is_gone(api_server):
    payload = {"path": "/audits/deadbeef0000/", "html": "<script>alert(1)</script>"}
    status, _headers, body = request(api_server, "POST", "/api/reports/deploy", token="token-a", body=payload)
    assert status == 404
    assert b"not found" in body.lower()


def test_report_and_artifact_paths_cannot_bypass_ownership(api_server):
    audit = create_audit(api_server)
    job_id = audit["id"]
    report = server.GTM_VERCEL_DIR / "audits" / job_id / "index.html"
    report.parent.mkdir(parents=True)
    report.write_text("safe report", encoding="utf-8")
    artifact = server.GENERATED_DIR / "screenshot-audits" / job_id / "uploads" / "one.png"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"image")
    report_path = f"/audits/{job_id}/"
    artifact_path = "/artifacts/" + artifact.relative_to(server.ROOT_DIR).as_posix() if server.ROOT_DIR in artifact.parents else ""
    assert request(api_server, "GET", report_path, token="token-a")[0] == 200
    assert request(api_server, "GET", report_path, token="token-b")[0] == 404
    # Direct generated files outside a recognized owned job directory are denied.
    unowned = server.GENERATED_DIR / "orphan.txt"
    unowned.write_text("legacy", encoding="utf-8")
    assert server._artifact_job_id(unowned) == ""


def test_website_workspace_report_resolves_by_job_id_without_sibling_search(api_server, monkeypatch, tmp_path):
    monkeypatch.setattr(server, "AUDITS_DIR", tmp_path / "audits")
    audit = create_audit(api_server)
    workspace = AuditWorkspace(audit["id"], server.AUDITS_DIR)
    workspace.prepare(mode="gtm")
    report = workspace.publication / "audits" / audit["id"] / "index.html"
    report.parent.mkdir(parents=True)
    report.write_text("workspace report", encoding="utf-8")

    assert request(api_server, "GET", f"/audits/{audit['id']}/", token="token-a")[0] == 200
    assert request(api_server, "GET", f"/audits/{audit['id']}/", token="token-b")[0] == 404


def test_persisted_ownership_protects_report_after_job_memory_is_gone(api_server):
    audit = create_audit(api_server)
    job_id = audit["id"]
    report = server.GTM_VERCEL_DIR / "audits" / job_id / "index.html"
    report.parent.mkdir(parents=True)
    report.write_text("safe report", encoding="utf-8")
    with server.JOBS_LOCK:
        server.JOBS.clear()
    assert request(api_server, "GET", f"/audits/{job_id}/", token="token-a")[0] == 200
    assert request(api_server, "GET", f"/audits/{job_id}/", token="token-b")[0] == 404


def test_static_report_symlink_component_is_denied(api_server, monkeypatch):
    audit = create_audit(api_server)
    job_id = audit["id"]
    report = server.GTM_VERCEL_DIR / "audits" / job_id / "index.html"
    report.parent.mkdir(parents=True)
    report.write_text("safe report", encoding="utf-8")
    original = server.Path.is_symlink
    monkeypatch.setattr(server.Path, "is_symlink", lambda self: self.name == job_id or original(self))
    assert request(api_server, "GET", f"/audits/{job_id}/", token="token-a")[0] == 404


def test_publish_requires_owner(api_server, monkeypatch):
    audit = create_audit(api_server)
    with server.JOBS_LOCK:
        server.JOBS[audit["id"]]["status"] = "completed"
    monkeypatch.setattr(server, "_publish_job_report", lambda _job: "https://example.vercel.app/audits/id/")
    path = f"/api/audits/{audit['id']}/publish"
    assert request(api_server, "POST", path, token="token-b")[0] == 404
    assert request(api_server, "POST", path, token="token-a")[0] == 200


def test_json_body_limit(api_server, monkeypatch):
    monkeypatch.setattr(server, "MAX_JSON_BODY_BYTES", 8)
    status, _headers, _body = request(api_server, "POST", "/api/audits", token="token-a", body=b"{" + b"x" * 20)
    assert status == 400


def test_authenticated_rate_limit_returns_retry_after(api_server, monkeypatch):
    monkeypatch.setenv("UX_RATE_LIMIT_PER_MINUTE", "1")
    assert request(api_server, "GET", "/api/criteria", token="token-a")[0] == 200
    status, headers, _body = request(api_server, "GET", "/api/criteria", token="token-a")
    assert status == 429
    assert int(headers["Retry-After"]) >= 1


def test_detailed_mode_capability_is_exposed_and_unavailable_mode_is_rejected(api_server, monkeypatch):
    monkeypatch.setattr(server, "_detailed_workbook_template_available", lambda: False)
    status, _headers, body = request(api_server, "GET", "/api/capabilities", token="token-a")
    assert status == 200
    assert json.loads(body) == {"detailedAuditAvailable": False}
    status, _headers, body = request(
        api_server,
        "POST",
        "/api/audits",
        token="token-a",
        body={"auditType": "website", "mode": "detailed", "url": "https://example.com/"},
    )
    assert status == 400
    assert b"workbook template" in body.lower()


def test_appium_target_cannot_be_selected_by_request(monkeypatch):
    monkeypatch.setenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
    assert server._trusted_appium_url("") == "http://127.0.0.1:4723"
    with pytest.raises(ValueError):
        server._trusted_appium_url("http://169.254.169.254/")
