"""The PDF is printed from the same client report HTML, with a client-ready filename."""
import re

from client_report_fixtures import REVISION, machine
from src.report.client import pdf
from src.report.client.context import build_client_report_context
from src.report.client.render import render_client_report
from test_client_report_routes import seeded
from test_server_security import api_server, request  # noqa: F401


def test_render_pdf_prints_a_multi_page_a4_document():
    context = build_client_report_context(audit_id="a", machine=machine(), revision=REVISION, audit_date="2026-10-06")
    document = pdf.render_pdf(render_client_report(context))
    assert document.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page[^s]", document)) >= 3


def test_pdf_filename_is_a_safe_slug():
    assert pdf.pdf_filename("Managers.tn / <Home>", "2026-10-06") == "managers-tn-home-ux-audit-2026-10-06.pdf"
    assert pdf.pdf_filename("", "2026-10-06") == "audit-ux-audit-2026-10-06.pdf"


def test_owner_downloads_the_pdf(api_server, monkeypatch):
    job_id = seeded(api_server)
    monkeypatch.setattr(pdf, "render_pdf", lambda html, **_: b"%PDF-1.7 fake")
    status, headers, body = request(api_server, "GET", f"/api/audits/{job_id}/client-report.pdf", token="token-a")
    assert status == 200 and body == b"%PDF-1.7 fake" and headers["Content-Type"] == "application/pdf"
    assert re.fullmatch(r'attachment; filename="[a-z0-9-]+-ux-audit-\d{4}-\d{2}-\d{2}\.pdf"', headers["Content-Disposition"])


def test_other_owner_cannot_download_the_pdf(api_server, monkeypatch):
    job_id = seeded(api_server)
    monkeypatch.setattr(pdf, "render_pdf", lambda html, **_: b"%PDF")
    assert request(api_server, "GET", f"/api/audits/{job_id}/client-report.pdf", token="token-b")[0] == 404


def test_pdf_failure_is_reported_without_details(api_server, monkeypatch):
    job_id = seeded(api_server)

    def broken(html, **_):
        raise pdf.PdfExportError("chromium missing at C:/secret/path")

    monkeypatch.setattr(pdf, "render_pdf", broken)
    status, _, body = request(api_server, "GET", f"/api/audits/{job_id}/client-report.pdf", token="token-a")
    assert status == 503 and b"PDF export is temporarily unavailable." in body and b"secret" not in body


def test_long_unbreakable_text_never_overflows_the_printed_page():
    from playwright.sync_api import sync_playwright
    data = machine()
    long_url = "https://managers.tn/" + "very-long-path-segment-" * 12
    for finding in data["deduplicatedFindings"]:
        finding["title"] = "See " + long_url
        finding["pageUrl"] = long_url
    revision = {**REVISION, "changes": {**REVISION["changes"], "d1": {**REVISION["changes"]["d1"], "reviewNote": "Note " + "x" * 300}}}
    html = render_client_report(build_client_report_context(audit_id="a", machine=data, revision=revision, audit_date="2026-10-06"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123})
        page.set_content(html)
        page.emulate_media(media="print")
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        browser.close()
    assert overflow <= 0


def test_unreachable_web_font_does_not_block_the_pdf(monkeypatch):
    import time
    # A non-routable address: requests to it hang instead of failing fast.
    monkeypatch.setattr(pdf, "FONT_HOSTS", pdf.FONT_HOSTS + ("http://10.255.255.1/",))
    html = '<!doctype html><html><head><link rel="stylesheet" href="http://10.255.255.1/font.css"></head><body><p>Report</p></body></html>'
    started = time.monotonic()
    assert pdf.render_pdf(html).startswith(b"%PDF")
    assert time.monotonic() - started < 20
