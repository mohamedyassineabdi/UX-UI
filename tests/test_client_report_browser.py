"""In-app client report: default view, PDF download, readable review details, AI agent wording.

Run npm run build first.
"""
from playwright.sync_api import expect

from src.report.client import pdf
from src.ui import server
from test_frontend_browser import axe, browser, complete, ui  # noqa: F401
from test_server_security import api_server  # noqa: F401


def open_report(page):
    page.get_by_role("link", name="Open report", exact=True).click()
    expect(page.get_by_text("Local report", exact=True)).to_be_visible()


def test_client_report_is_the_default_view(ui):
    page, _, _ = ui
    complete(page, wait_for_review=False)
    open_report(page)
    expect(page.get_by_role("button", name="Client report", exact=True)).to_have_attribute("aria-pressed", "true")
    frame = page.frame_locator('iframe[title="Client report"]')
    expect(frame.locator("#executive-summary")).to_be_visible(timeout=10000)
    expect(frame.locator("#next-steps")).to_have_count(0)
    page.get_by_role("button", name="Review / Edit", exact=True).click()
    expect(page.get_by_label("Review decision")).to_be_visible()


def test_download_pdf_saves_a_named_file(ui, monkeypatch):
    page, _, _ = ui
    monkeypatch.setattr(pdf, "render_pdf", lambda html, **_: b"%PDF-1.7 test")
    complete(page, wait_for_review=False)
    open_report(page)
    with page.expect_download() as download:
        page.get_by_role("button", name="Download PDF", exact=True).click()
    assert download.value.suggested_filename.endswith(".pdf") and "-ux-audit-" in download.value.suggested_filename


def test_pdf_failure_is_shown_inline(ui, monkeypatch):
    page, _, _ = ui

    def broken(html, **_):
        raise pdf.PdfExportError("browser missing")

    monkeypatch.setattr(pdf, "render_pdf", broken)
    complete(page, wait_for_review=False)
    open_report(page)
    page.get_by_role("button", name="Download PDF", exact=True).click()
    expect(page.get_by_text("PDF export is temporarily unavailable.")).to_be_visible()


def test_review_details_are_readable_not_code(ui):
    page, _, _ = ui
    complete(page)
    page.get_by_text("Finding details", exact=True).click()
    details = page.locator(".readable-record").last
    expect(details).to_contain_text("Severity")
    assert "{" not in details.inner_text() and '":' not in details.inner_text()
    page.get_by_text("Evidence provenance & check details", exact=True).click()
    assert "{" not in page.locator(".provenance").inner_text()


def test_dropdowns_have_a_spaced_custom_arrow(ui):
    page, _, _ = ui
    complete(page)
    select = page.get_by_label("Review decision")
    style = select.evaluate("e => { const s = getComputedStyle(e); return [s.appearance, parseFloat(s.paddingRight), s.backgroundImage] }")
    assert style[0] == "none" and style[1] >= 36 and "svg" in style[2]


def test_ai_review_copy_names_the_ai_agent_never_the_model(ui):
    page, _, _ = ui
    complete(page)
    job_id = page.evaluate("sessionStorage.getItem('uxui-current-audit')")
    server.JOB_STORE.update(job_id, aiReviewStatus="running")
    page.reload()
    expect(page.get_by_text("The AI agent is reviewing the screenshots", exact=False)).to_be_visible(timeout=10000)
    server.JOB_STORE.update(job_id, aiReviewStatus="failed", aiReviewError="AI review did not finish: Claude CLI is not available")
    page.reload()
    expect(page.get_by_text("The AI review didn’t finish")).to_be_visible(timeout=10000)
    assert "Claude" not in page.locator("body").text_content()


def test_ai_findings_can_be_reviewed(ui):
    page, _, _ = ui
    def with_ai_finding(machine):
        machine["aiDiscoveredFindings"] = [{"title": "Hero headline is cut off", "severity": "medium", "axisName": "Accessibility", "evidence": "Truncated title.", "aiDiscovered": True}]
    complete(page, transform=with_ai_finding)
    page.get_by_role("button", name="Hero headline is cut off").click()
    expect(page.get_by_label("Review decision")).to_be_enabled()


def test_report_frame_lets_links_open_in_a_new_tab(ui):
    page, _, _ = ui
    complete(page, wait_for_review=False)
    open_report(page)
    sandbox = page.get_by_title("Client report").get_attribute("sandbox")
    assert "allow-popups" in sandbox and "allow-popups-to-escape-sandbox" in sandbox and "allow-scripts" not in sandbox


def test_lowercase_model_name_never_reaches_the_ai_review_banner(ui):
    page, _, _ = ui
    complete(page)
    job_id = page.evaluate("sessionStorage.getItem('uxui-current-audit')")
    server.JOB_STORE.update(job_id, aiReviewStatus="failed", aiReviewError="AI review did not finish: cannot find the file specified: 'claude'")
    page.reload()
    expect(page.get_by_text("The AI review didn’t finish")).to_be_visible(timeout=10000)
    assert "claude" not in page.locator("body").text_content().lower()
