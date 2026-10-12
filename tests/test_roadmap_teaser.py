from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from src.report import roadmap_teaser as rt


DEFAULT_URL = "https://cal.com/sofiene-m-hadheb-nwve91/30min"
SENTINEL = "SENTINEL_FIX_TEXT"


def finding(fid, severity, axis="usability", outcome="fail", **extra):
    return {"findingId": fid, "severity": severity, "axisId": axis, "outcome": outcome,
            "recommendation": SENTINEL, "fix": SENTINEL, "recommendedFix": SENTINEL, **extra}


FINDINGS = [
    finding("f1", "critical", "accessibility"),
    finding("f2", "high", "usability"),
    finding("f3", "medium", "content"),
    finding("f4", "low", "content"),
    finding("f5", "medium", "visual", deduplicationId="d1"),
    finding("f6", "medium", "visual", deduplicationId="d1"),
    finding("f7", "high", "usability", outcome="pass"),
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("EXPERT_BOOKING_URL", "EXPERT_NAME", "EXPERT_PHOTO_URL"):
        monkeypatch.delenv(key, raising=False)


def test_default_config_uses_the_expert_and_booking_link():
    config = rt.expert_booking_config()
    assert config.url == DEFAULT_URL
    assert config.name == "Sofiene Mhadheb"
    assert "EY Studio+" in config.title["en"] and "EY Studio+" in config.title["fr"]
    assert config.photo_url is None


def test_empty_booking_url_disables_every_output(monkeypatch):
    monkeypatch.setenv("EXPERT_BOOKING_URL", "")
    assert rt.expert_booking_config() is None
    assert rt.teaser_payload(FINDINGS, lang="en", site_url="https://a.test", report_url=None) is None
    assert rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url="https://a.test") == ""


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://evil.com/x", "http://cal.com/x", "https://cal.com.evil.com/x", "https://evil.com\@cal.com/x", "https://user@cal.com/x", "https://cal.com:8443/x"])
def test_non_cal_com_booking_urls_are_rejected(monkeypatch, url):
    monkeypatch.setenv("EXPERT_BOOKING_URL", url)
    assert rt.expert_booking_config() is None
    assert rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url="https://a.test") == ""


def test_counts_split_failing_findings_by_severity_and_dedupe():
    assert rt.teaser_counts(FINDINGS) == {"quickWins": 3, "structural": 2, "axes": 4}


def test_counts_ignore_non_dict_entries_and_read_axis_alias():
    assert rt.teaser_counts([None, "x", {"findingId": "a", "severity": "High", "axis": "trust"}]) == {"quickWins": 0, "structural": 1, "axes": 1}


def test_zero_findings_render_clean_audit_copy():
    html = rt.render_roadmap_teaser_html([], lang="en", site_url="https://a.test")
    assert 'id="roadmap-teaser"' in html
    assert rt.teaser_copy("en")["cleanHeading"] in html


def test_untrusted_urls_are_escaped_and_encoded():
    site = 'https://a.test/?q="<img onerror=x>&x'
    html = rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url=site, report_url="https://r.test/<b>")
    assert "<img onerror" not in html and "<b>" not in html
    url = rt.booking_url(DEFAULT_URL, site_url=site, report_url="https://r.test/x", embed=True)
    query = parse_qs(urlparse(url).query)
    assert query["embed"] == ["true"]
    assert site in query["notes"][0] and "https://r.test/x" in query["notes"][0]


def test_no_recommendation_text_reaches_markup_or_payload():
    html = rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url="https://a.test")
    payload = rt.teaser_payload(FINDINGS, lang="en", site_url="https://a.test", report_url=None)
    assert SENTINEL not in html
    assert SENTINEL not in json.dumps(payload)


def test_payload_shape_for_clients():
    payload = rt.teaser_payload(FINDINGS, lang="fr", site_url="https://a.test", report_url=None)
    assert payload["enabled"] is True
    assert payload["counts"]["structural"] == 2
    assert payload["bookingUrl"].startswith(DEFAULT_URL) and "embed=true" not in payload["bookingUrl"]
    assert "embed=true" in payload["embedUrl"]
    assert payload["expert"]["initials"] == "SM"
    assert payload["copy"] == rt.teaser_copy("fr")


def test_cta_is_a_real_new_tab_link_and_modal_has_embed_iframe():
    html = rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url="https://a.test")
    assert 'target="_blank"' in html and 'rel="noopener"' in html
    assert "<dialog" in html and "<iframe" in html and "embed=true" in html


def test_french_copy_and_unknown_language_falls_back_to_english():
    assert rt.teaser_copy("fr")["cta"] != rt.teaser_copy("en")["cta"]
    assert rt.teaser_copy("de") == rt.teaser_copy("en")
    html = rt.render_roadmap_teaser_html(FINDINGS, lang="fr", site_url="https://a.test")
    assert rt.teaser_copy("fr")["cta"] in html and 'lang="fr"' in html



def test_chips_use_singular_labels_for_one_item():
    one_each = [finding("a", "high", "usability"), finding("b", "low", "usability")]
    html = rt.render_roadmap_teaser_html(one_each, lang="en", site_url="https://a.test")
    assert "<strong>1</strong> quick win<" in html and "<strong>1</strong> structural change<" in html
    assert "<strong>1</strong> area to improve<" in html
    fr = rt.render_roadmap_teaser_html(one_each, lang="fr", site_url="https://a.test")
    assert "<strong>1</strong> gain rapide<" in fr


def test_teaser_styles_come_from_the_shared_stylesheet():
    css = (rt.STYLESHEET_PATH).read_text(encoding="utf-8")
    assert ".rt-card" in css
    assert css.strip() in rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url="https://a.test")

# --- Task 2: exported report surfaces ---------------------------------------

from src.gtm_audit.generate_gtm_report import render_html  # noqa: E402
from src.report.reviewed_report import render_reviewed_report, reviewed_report_context  # noqa: E402

GTM_PAYLOAD = {
    "site": {"display_name": "Acme", "homepage": "https://acme.test"},
    "executiveSummary": {"axesScored": 1, "axesTotal": 5},
    "axes": [{"id": "usability", "painPoints": [{"title": "Broken form", "severity": "high", "recommendation": SENTINEL}]}],
}


def test_findings_from_report_prefers_full_list_then_axis_pain_points():
    assert rt.findings_from_report({"allFindings": [{"findingId": "a"}]}) == [{"findingId": "a"}]
    flattened = rt.findings_from_report(GTM_PAYLOAD)
    assert flattened[0]["axisId"] == "usability" and flattened[0]["severity"] == "high"
    assert rt.findings_from_report({}) == []


def test_gtm_report_places_teaser_once_before_footer(tmp_path):
    report = render_html(GTM_PAYLOAD, tmp_path)
    assert report.count('id="roadmap-teaser"') == 1
    assert report.index('id="roadmap-teaser"') < report.index('<footer class="footer">')
    assert SENTINEL not in report.split('id="roadmap-teaser"', 1)[1].split("</section>", 1)[0]
    assert "mail.google.com" not in report


def test_reviewed_report_places_expert_cta_after_findings_before_appendix():
    context = reviewed_report_context(audit_id="a1", machine={"allFindings": FINDINGS, "site": {"homepage": "https://acme.test"}}, revision=None)
    report = render_reviewed_report(context)
    assert report.count('id="next-steps"') == 1
    assert report.index('id="findings"') < report.index('id="next-steps"') < report.index('id="appendix"')


def test_exported_reports_omit_teaser_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("EXPERT_BOOKING_URL", "")
    context = reviewed_report_context(audit_id="a1", machine={"allFindings": FINDINGS}, revision=None)
    assert "roadmap-teaser" not in render_html(GTM_PAYLOAD, tmp_path)
    assert "next-steps" not in render_reviewed_report(context)


# --- Task 3: server endpoint and CSP ----------------------------------------

from test_server_security import api_server, create_audit, request  # noqa: E402,F401


def _teaser(api_server, job_id, token="token-a", query=""):
    status, headers, body = request(api_server, "GET", f"/api/audits/{job_id}/roadmap-teaser{query}", token=token)
    return status, headers, json.loads(body or b"{}")


def test_roadmap_teaser_endpoint_returns_counts_without_recommendation_text(api_server, monkeypatch):
    server = __import__("src.ui.server", fromlist=["server"])
    monkeypatch.setattr(server, "_machine_audit_data", lambda job_id: {"allFindings": FINDINGS})
    job_id = create_audit(api_server)["id"]
    status, _headers, payload = _teaser(api_server, job_id, query="?lang=fr")
    assert status == 200
    assert payload["enabled"] is True and payload["counts"] == {"quickWins": 3, "structural": 2, "axes": 4}
    assert payload["copy"] == rt.teaser_copy("fr")
    assert "example.com" in payload["bookingUrl"]
    assert SENTINEL not in json.dumps(payload)


def test_roadmap_teaser_endpoint_requires_auth_and_ownership(api_server):
    job_id = create_audit(api_server)["id"]
    assert request(api_server, "GET", f"/api/audits/{job_id}/roadmap-teaser")[0] == 401
    assert _teaser(api_server, job_id, token="token-b")[0] == 404
    assert _teaser(api_server, "missing-job")[0] == 404


def test_roadmap_teaser_endpoint_reports_disabled(api_server, monkeypatch):
    monkeypatch.setenv("EXPERT_BOOKING_URL", "")
    job_id = create_audit(api_server)["id"]
    status, _headers, payload = _teaser(api_server, job_id)
    assert (status, payload) == (200, {"enabled": False})


def test_csp_allows_cal_com_frames_only_when_booking_enabled(api_server, monkeypatch):
    _status, headers, _ = request(api_server, "GET", "/api/criteria", token="token-a")
    csp = headers["Content-Security-Policy"]
    assert "frame-src https://cal.com https://app.cal.com" in csp
    assert "script-src 'self' 'unsafe-inline'; frame-src" in csp and "  " not in csp
    monkeypatch.setenv("EXPERT_BOOKING_URL", "")
    _status, headers, _ = request(api_server, "GET", "/api/criteria", token="token-a")
    assert "frame-src" not in headers["Content-Security-Policy"] and "  " not in headers["Content-Security-Policy"]



# --- Final review fixes --------------------------------------------------------

def test_booking_dialog_offers_a_new_tab_fallback_link():
    html = rt.render_roadmap_teaser_html(FINDINGS, lang="en", site_url="https://a.test")
    dialog = html.split("<dialog", 1)[1].split("</dialog>", 1)[0]
    assert 'href="https://cal.com/sofiene-m-hadheb-nwve91/30min?' in dialog and 'target="_blank"' in dialog
    assert rt.teaser_copy("en")["openNewTab"] in dialog


def test_zero_count_chips_are_not_shown():
    html = rt.render_roadmap_teaser_html([finding("a", "high", "usability")], lang="en", site_url="https://a.test")
    assert "<strong>0</strong>" not in html
    assert "<strong>1</strong> structural change<" in html


def test_reviewed_report_counts_exclude_suppressed_findings():
    revision = {"revisionId": "r1", "changes": {"f1": {"suppressed": True, "suppressionReason": "False positive"}}}
    context = reviewed_report_context(audit_id="a1", machine={"allFindings": FINDINGS}, revision=revision)
    report = render_reviewed_report(context)
    teaser = report.split('id="next-steps"', 1)[1]
    assert "<strong>1</strong> structural change<" in teaser
