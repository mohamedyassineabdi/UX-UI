from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_structured_review_ui_keeps_actions_and_revision_identity_separate():
    html = (ROOT / "src" / "ui" / "static" / "index.html").read_text(encoding="utf-8")
    assert "function ReviewWorkspace" in html
    assert "/review`" in html and "/revisions`" in html
    assert "${action}`" in html
    assert "body: JSON.stringify(revisionId ? { revisionId } : {})" in html
    assert "Review revision saved. It has not been validated or published." in html
    assert "Revision validated. It has not been published." in html
    assert "Publish machine report — not reviewed" in html
    assert "Recent revision history" in html
    assert "This review was changed in another session. Refresh before saving again." in html


def test_review_ui_renders_reviewer_values_without_html_sinks():
    html = (ROOT / "src" / "ui" / "static" / "index.html").read_text(encoding="utf-8")
    assert "dangerouslySetInnerHTML" not in html
    assert "innerHTML" not in html
    assert "contenteditable" not in html.lower()


def test_active_machine_report_surfaces_identify_integrity_metadata():
    gtm = (ROOT / "src" / "gtm_audit" / "generate_gtm_report.py").read_text(encoding="utf-8")
    detailed = (ROOT / "src" / "report" / "generate_audit_report.py").read_text(encoding="utf-8")
    figma = (ROOT / "figma_audit" / "reports.py").read_text(encoding="utf-8")
    for content in (gtm, detailed, figma):
        assert "Machine audit" in content
        assert "not reviewed" in content
        assert "Methodology" in content
        assert "Limitations" in content
    assert "uploaded screenshots/surfaces analyzed" in gtm
    assert "screens/actions explored within configured exploration bounds" in gtm
    assert "Figma pages, frames, components, and rendered surfaces" in figma
