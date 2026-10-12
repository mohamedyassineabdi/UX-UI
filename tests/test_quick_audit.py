"""Quick / deep audit depth: request validation, profiles, page choice, time budget, timeout errors."""
import json
import sys

import pytest

from src.audit.discovery import DiscoveredPage, is_page_url, merge_candidates, select_pages
from src.audit.time_budget import TimeBudget, heavy_step_skip_reason
from src.ui import server
from test_server_security import api_server, request  # noqa: F401  (fixture reuse)


# --- request validation -------------------------------------------------------

def _create(instance, **extra):
    body = {"auditType": "website", "mode": "gtm", "url": "https://example.com/", **extra}
    return request(instance, "POST", "/api/audits", token="token-a", body=body)


def test_depth_defaults_to_quick(api_server):
    status, _, body = _create(api_server)
    assert status == 202 and json.loads(body)["depth"] == "quick"


def test_deep_depth_is_accepted(api_server):
    status, _, body = _create(api_server, depth="deep")
    assert status == 202 and json.loads(body)["depth"] == "deep"


def test_unknown_depth_is_rejected(api_server):
    assert _create(api_server, depth="turbo")[0] == 400


# --- depth profiles -----------------------------------------------------------

def test_quick_profile():
    profile = server._depth_profile("quick")
    assert profile.env == {
        "UX_AUDIT_MAX_PAGES": "2",
        "UX_LIGHTHOUSE_MAX_PAGES": "1",
        "UX_AUDIT_INTERACTION_MAX_PAGES": "1",
        "AUDIT_NAVIGATION_TIMEOUT_MS": "10000",
        "AUDIT_NETWORK_IDLE_TIMEOUT_MS": "2000",
        "UX_SITEMAP_MAX_FILES": "1",
        "UX_SITEMAP_MAX_URLS": "50",
        "AUDIT_MAX_SAFE_INTERACTIONS_PER_PAGE": "5",
    }
    assert (profile.budget_sec, profile.hard_stop_sec) == (60, 180)


def test_deep_profile():
    profile = server._depth_profile("deep")
    assert profile.env["UX_AUDIT_MAX_PAGES"] == "10" and profile.env["UX_LIGHTHOUSE_MAX_PAGES"] == "3"
    assert "AUDIT_NAVIGATION_TIMEOUT_MS" not in profile.env
    assert (profile.budget_sec, profile.hard_stop_sec) == (360, 600)


def test_jobs_without_depth_run_as_quick():
    assert server._depth_profile(None) == server._depth_profile("quick")


# --- hard-stop errors ---------------------------------------------------------

@pytest.fixture
def store_job(monkeypatch, tmp_path):
    from src.jobs.store import JobStore

    store = JobStore(tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(server, "JOB_STORE", store)
    job = server._new_job("https://example.com/", "gtm")
    store.create(job, owner_id="user-a", owner_role="reviewer")
    server._set_job(job["id"], status="running", startedAt=server._now(), stage="Opening pages (4/50)")
    return job["id"]


def test_hard_stop_names_the_stage_and_elapsed_time(store_job):
    code = server._run_command(store_job, [sys.executable, "-c", "import time; time.sleep(5)"],
                               stage="Running audit pipeline", progress=5, stage_timeout=0.4)
    job = server.JOB_STORE.get(store_job)
    assert code == server.TIMEOUT_RETURN_CODE
    assert job["status"] == "failed"
    assert job["error"].startswith("Stopped after ") and "while running audit pipeline" in job["error"]


def test_pipeline_timeout_error_is_not_overwritten(store_job, monkeypatch):
    def fake_run_command(job_id, *_args, **_kwargs):
        server._set_job(job_id, status="failed", error="Stopped after 3 min while opening pages.")
        return server.TIMEOUT_RETURN_CODE

    monkeypatch.setattr(server, "_run_command", fake_run_command)
    server._run_audit_job(store_job)
    assert server.JOB_STORE.get(store_job)["error"] == "Stopped after 3 min while opening pages."


def test_pipeline_gets_profile_env_and_deadline(store_job, monkeypatch):
    seen = {}

    def fake_run_command(job_id, command, **kwargs):
        seen.update(kwargs)
        return 1

    monkeypatch.setattr(server, "_run_command", fake_run_command)
    server._run_audit_job(store_job)
    env = seen["env_overrides"]
    assert env["UX_AUDIT_MAX_PAGES"] == "2"
    started = float(server.JOB_STORE.get(store_job).get("startedAt") or server._now())  # worker sets startedAt on claim
    assert float(env["UX_AUDIT_DEADLINE"]) == pytest.approx(started + 60, abs=2)
    assert seen["stage_timeout"] == 180


# --- discovery ----------------------------------------------------------------

@pytest.mark.parametrize("url, expected", [
    ("https://site.tn/category/banking/", True),
    ("https://site.tn/", True),
    ("https://site.tn/page.html", True),
    ("https://site.tn/wp-content/uploads/a.png", False),
    ("https://site.tn/wp-content/uploads/b.JPEG", False),
    ("https://site.tn/files/report.pdf", False),
    ("https://site.tn/video.mp4?x=1", False),
])
def test_is_page_url(url, expected):
    assert is_page_url(url) is expected


def test_sitemap_media_files_are_excluded_as_not_a_page():
    pages = merge_candidates([
        {"url": "https://site.tn/", "source": "homepage"},
        {"url": "https://site.tn/wp-content/uploads/a.png", "source": "sitemap"},
    ], "https://site.tn/", include_auth_pages=False)
    image = next(p for p in pages if p.canonical_url.endswith(".png"))
    assert (image.selection_status, image.exclusion_reason) == ("excluded", "not_a_page")


def _page(url, source="navigation", **kwargs):
    return DiscoveredPage(url, url, "", {source}, **kwargs)


def test_quick_selection_is_homepage_then_first_menu_page():
    pages = [_page("https://site.tn/privacy", "footer"), _page("https://site.tn/zeta"), _page("https://site.tn/alpha"),
             _page("https://site.tn/", "homepage"), _page("https://site.tn/x.png", "sitemap")]
    select_pages(pages, 2, navigation_order=["https://site.tn/zeta", "https://site.tn/alpha"])
    selected = sorted(p.canonical_url for p in pages if p.selection_status == "selected")
    assert selected == ["https://site.tn/", "https://site.tn/zeta"]
    assert next(p for p in pages if p.canonical_url.endswith(".png")).exclusion_reason == "not_a_page"


def test_selection_without_navigation_order_still_prefers_menu_pages_over_legal():
    pages = [_page("https://site.tn/privacy", "footer"), _page("https://site.tn/products"), _page("https://site.tn/", "homepage")]
    select_pages(pages, 2)
    assert {p.canonical_url for p in pages if p.selection_status == "selected"} == {"https://site.tn/", "https://site.tn/products"}


# --- time budget --------------------------------------------------------------

def test_time_budget_from_deadline(monkeypatch):
    now = [1000.0]
    monkeypatch.setenv("UX_AUDIT_DEADLINE", "1060")
    budget = TimeBudget.from_env(clock=lambda: now[0])
    assert not budget.exhausted() and budget.remaining() == 60
    now[0] = 1061
    assert budget.exhausted()


def test_time_budget_unlimited_without_deadline(monkeypatch):
    monkeypatch.delenv("UX_AUDIT_DEADLINE", raising=False)
    budget = TimeBudget.from_env()
    assert not budget.exhausted() and budget.remaining() is None


@pytest.mark.parametrize("index, limit, exhausted, expected", [
    (0, 1, False, None),
    (1, 1, False, "page_limit"),
    (0, 1, True, "time_budget"),
    (5, None, False, None),
])
def test_heavy_step_skip_reason(index, limit, exhausted, expected):
    budget = TimeBudget(deadline=0.0 if exhausted else None, clock=lambda: 1.0)
    assert heavy_step_skip_reason(index, limit, budget) == expected


def test_navigation_timeouts_follow_env(monkeypatch):
    import importlib

    from src.config import audit_config

    monkeypatch.setenv("AUDIT_NAVIGATION_TIMEOUT_MS", "10000")
    monkeypatch.setenv("AUDIT_NETWORK_IDLE_TIMEOUT_MS", "2000")
    reloaded = importlib.reload(audit_config)
    try:
        config = reloaded.AUDIT_CONFIG
        assert config["navigation"]["timeoutMs"] == 10000
        assert config["pageReadiness"]["networkIdleTimeoutMs"] == 2000
    finally:
        monkeypatch.delenv("AUDIT_NAVIGATION_TIMEOUT_MS")
        monkeypatch.delenv("AUDIT_NETWORK_IDLE_TIMEOUT_MS")
        importlib.reload(audit_config)


def test_navigation_order_reads_top_level_menu_then_children():
    from src.audit.discovery import navigation_order

    menu = {"homepage": "https://site.tn/", "navigation": [
        {"name": "Banking", "url": "https://site.tn/banking/", "children": [{"name": "Loans", "url": "https://site.tn/loans/"}]},
        {"name": "Search", "url": None, "children": []},
        {"name": "Tech", "url": "https://site.tn/tech/", "children": []},
    ]}
    assert navigation_order(menu) == ["https://site.tn/banking/", "https://site.tn/tech/", "https://site.tn/loans/"]
    assert navigation_order({}) == [] and navigation_order(None) == []
