from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_structured_review_ui_keeps_actions_and_revision_identity_separate():
    panel = (ROOT / "src" / "ui" / "frontend" / "review" / "ReviewPanel.jsx").read_text(encoding="utf-8")
    reviews = (ROOT / "src" / "ui" / "frontend" / "api" / "reviews.js").read_text(encoding="utf-8")
    publications = (ROOT / "src" / "ui" / "frontend" / "api" / "publications.js").read_text(encoding="utf-8")
    assert "Save revision" in panel and "Validate" in panel and "Approve" in panel
    assert "Publish reviewed report" in panel and "Revision history" in panel
    assert "This review was changed in another session. Refresh before saving again." in panel
    assert "/revisions`" in reviews and "${action}`" in reviews
    assert "body: JSON.stringify(revisionId ? { revisionId } : {})" in publications


def test_review_ui_renders_reviewer_values_without_html_sinks():
    frontend = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "ui" / "frontend").rglob("*.jsx"))
    assert "dangerouslySetInnerHTML" not in frontend
    assert "innerHTML" not in frontend
    assert "contenteditable" not in frontend.lower()


def test_active_machine_report_surfaces_identify_integrity_metadata():
    gtm = (ROOT / "src" / "gtm_audit" / "generate_gtm_report.py").read_text(encoding="utf-8")
    detailed = (ROOT / "src" / "report" / "generate_audit_report.py").read_text(encoding="utf-8")
    figma = (ROOT / "figma_audit" / "reports.py").read_text(encoding="utf-8")
    for content in (gtm, detailed, figma):
        assert "Machine audit" in content and "not reviewed" in content
        assert "Methodology" in content and "Limitations" in content
    assert "uploaded screenshots/surfaces analyzed" in gtm
    assert "screens/actions explored within configured exploration bounds" in gtm
    assert "Figma pages, frames, components, and rendered surfaces" in figma
