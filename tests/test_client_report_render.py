"""The client report is one self-contained, script-free, consulting-grade HTML document."""
import re

from client_report_fixtures import REVISION, machine
from src.report.client.context import build_client_report_context, client_context_from_reviewed
from src.report.client import render
from src.report.client.render import render_client_report
from src.report.reviewed_report import render_reviewed_report, reviewed_report_context

IMAGES = {"ai-0": "data:image/jpeg;base64,AAAA"}
SECTIONS = ["cover", "executive-summary", "scorecard", "insights", "findings", "roadmap", "appendix"]


def report(data=None, images=IMAGES, revision=REVISION):
    context = build_client_report_context(audit_id="audit-1", machine=machine() if data is None else data, revision=revision, audit_date="2026-10-06")
    return render_client_report(context, images)


def test_sections_render_in_order():
    html = report()
    positions = [html.index(f'id="{section}"') for section in SECTIONS]
    assert positions == sorted(positions)


def test_only_cropped_findings_get_images():
    html = report()
    assert html.count("<img") == 1 and 'src="data:image/jpeg;base64,AAAA"' in html


def test_document_is_self_contained_and_script_free(monkeypatch):
    monkeypatch.setattr(render, "teaser_payload", lambda *a, **k: None)
    html = report()
    assert "<script" not in html.lower()
    for url in re.findall(r'(?:src|href)="([^"]+)"', html):
        assert url.startswith(("data:", "#", "https://managers.tn", "https://fonts.googleapis.com", "https://fonts.gstatic.com")), url


def test_hostile_text_is_escaped():
    data = machine()
    data["deduplicatedFindings"][1]["title"] = '<script>alert(1)</script>"><img onerror=x>'
    data["deduplicatedFindings"][1]["pageUrl"] = "javascript:alert(1)"
    html = report(data)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html and "<img onerror" not in html and "javascript:" not in html


def test_client_copy_never_names_the_model_or_internal_jargon():
    html = report()
    for word in ("Claude", "VLM", "machine finding", "Machine finding"):
        assert word not in html
    for raw in ("standards_automated", "deterministic_check", "axe-core", "button.icon"):
        assert raw not in html
    assert "Identified by the AI agent" in html


def test_key_facts_are_presented():
    html = report()
    assert "managers.tn" in html and "UX/UI Audit Report" in html and "6 October 2026" in html
    assert "Give every icon button an accessible name." in html and "Reviewer priority: critical" in html
    assert "Excluded by reviewer" in html and "Duplicate finding" in html and "Duplicate of d2" in html
    assert "Reviewed and validated by EY Studio+" in html
    for label in ("The problem", "Why it matters", "Recommendation", "Strength areas", "Critical improvement areas", "Now", "Next", "Later"):
        assert label in html


def test_print_rules_keep_cards_whole_on_a4():
    html = report()
    assert "@page" in html and "size: A4" in html and "break-inside: avoid" in html


def test_empty_sections_are_omitted():
    html = report({}, revision=None)
    assert 'id="cover"' in html and 'id="findings"' not in html and 'id="roadmap"' not in html


def test_unsafe_image_values_are_ignored():
    html = report(images={"ai-0": "javascript:alert(1)", "d1": "https://evil.test/x.png"})
    assert "<img" not in html


def test_legacy_reviewed_render_delegates_to_client_report():
    finding = {"deduplicationId": "defect_123", "title": "Contrast", "evidenceIds": ["e1"]}
    revision = {"revisionId": "a" * 32, "changes": {"defect_123": {"priorityOverride": "critical", "reviewedRecommendation": "Use <strong>contrast</strong>"}}}
    reviewed = reviewed_report_context(audit_id="audit", machine={"deduplicatedFindings": [finding]}, revision=revision)
    assert len(client_context_from_reviewed(reviewed)["findings"]) == 1
    html = render_reviewed_report(reviewed)
    assert 'id="cover"' in html and "Reviewer priority: critical" in html and "Use &lt;strong&gt;contrast&lt;/strong&gt;" in html


def test_expert_cta_is_a_static_link_when_booking_is_configured(monkeypatch):
    payload = {"bookingUrl": "https://cal.example/expert?x=1", "expert": {"name": "Expert Name", "title": "Lead designer"},
               "copy": {"eyebrow": "Expert roadmap", "heading": "Turn this audit into a redesign", "body": "Book a session.", "cleanHeading": "", "cleanBody": "", "cta": "Book a call"}}
    monkeypatch.setattr(render, "teaser_payload", lambda *a, **k: payload)
    html = report()
    assert 'id="next-steps"' in html and 'href="https://cal.example/expert?x=1"' in html and "<script" not in html


def test_expert_cta_omitted_without_booking(monkeypatch):
    monkeypatch.setattr(render, "teaser_payload", lambda *a, **k: None)
    assert 'id="next-steps"' not in report()


def test_embedded_report_blends_into_the_app():
    context = build_client_report_context(audit_id="a", machine=machine(), revision=None, audit_date="2026-10-06")
    assert '<body class="embedded">' in render_client_report(context, embedded=True)
    assert '<body class="embedded">' not in render_client_report(context)


def test_embedded_links_open_outside_the_report_frame():
    context = build_client_report_context(audit_id="a", machine=machine(), revision=None, audit_date="2026-10-06")
    assert '<base target="_blank">' in render_client_report(context, embedded=True)


def test_appendix_explains_how_each_finding_was_verified():
    html = report()
    appendix = html[html.index('id="appendix"'):]
    assert "How each finding was verified" in appendix and "Evidence provenance" not in appendix
    assert "Automated accessibility test (WCAG)" in appendix and "AI agent review of screenshots" in appendix
    assert "WCAG 4.1.2" in appendix and "<th>Element</th>" not in appendix


def test_cover_is_a_static_dot_field_with_a_headline_that_breaks_only_at_dots():
    html = report()
    cover = html[html.index('id="cover"'):html.index('id="executive-summary"')]
    assert '<svg' in cover and 'class="cover-field"' in cover and 'aria-hidden="true"' in cover
    assert 'class="cover-title cover-title-xl">managers.<wbr>tn</h1>' in cover
    assert "Pages audited" in cover and "<script" not in html


def test_cover_headline_steps_down_for_long_domains():
    data = machine()
    data["site"]["domain"] = "longer-client-name.co.uk"
    assert 'class="cover-title cover-title-md">' in report(data)


def test_standard_column_is_dropped_when_no_finding_cites_a_wcag_criterion():
    data = machine()
    data["deduplicatedFindings"][0]["evidenceBundle"].pop("criterion")
    appendix = report(data)
    appendix = appendix[appendix.index('id="appendix"'):]
    assert "<th>Standard</th>" not in appendix and "<th>Page</th>" in appendix
