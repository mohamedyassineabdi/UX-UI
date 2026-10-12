"""Print the client report HTML to an A4 PDF with headless Chromium (same document as the web report)."""
from __future__ import annotations

import re
import threading

FONT_WAIT_MS = 5000  # web fonts are a nicety; never let a slow font host block the PDF
PRINTERS = threading.BoundedSemaphore(2)  # cap concurrent Chromium processes
FONT_HOSTS = ("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")
FOOTER = ('<div style="width:100%;padding:0 12mm;font:8px Arial,sans-serif;color:#5B6275;display:flex;justify-content:space-between">'
          '<span>EY Studio+ · UX/UI Audit Report · Confidential</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


class PdfExportError(RuntimeError):
    """Raised when the PDF cannot be produced; the message is for logs, never for clients."""


def pdf_filename(site_name: str, audit_date: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (site_name or "").lower()).strip("-") or "audit"
    return f"{slug}-ux-audit-{audit_date}.pdf"


def _allow_fonts_only(route) -> None:
    if route.request.url.startswith(FONT_HOSTS) or route.request.url.startswith("data:"):
        route.continue_()
    else:
        route.abort()


def render_pdf(html: str, *, timeout_ms: int = 60000) -> bytes:
    try:
        from playwright.sync_api import sync_playwright

        with PRINTERS, sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.set_default_timeout(timeout_ms)
                page.route("**/*", _allow_fonts_only)
                page.set_content(html, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("load", timeout=FONT_WAIT_MS)
                except Exception:
                    pass  # print with the system font fallback
                page.emulate_media(media="print")
                return page.pdf(format="A4", print_background=True, prefer_css_page_size=True,
                                display_header_footer=True, header_template="<span></span>", footer_template=FOOTER)
            finally:
                browser.close()
    except Exception as exc:  # Playwright raises several unrelated types; callers need one.
        raise PdfExportError(str(exc)) from exc
