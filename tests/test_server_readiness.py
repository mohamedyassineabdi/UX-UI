from pathlib import Path

from src.ui import server


def test_browser_check_reports_installed_chromium():
    # The test environment has Playwright's Chromium installed (browser e2e tests need it).
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        assert Path(playwright.chromium.executable_path).exists()
    assert server._browser_check() == "ok"


def test_browser_check_reports_missing_executable(monkeypatch):
    monkeypatch.setattr(server, "_BROWSER_OK", False)
    monkeypatch.setattr(server, "_chromium_executable", lambda: "Z:/nowhere/chrome.exe")
    assert server._browser_check() == "missing"


def test_browser_check_reports_unavailable_playwright(monkeypatch):
    def broken():
        raise ImportError("No module named 'playwright'")

    monkeypatch.setattr(server, "_BROWSER_OK", False)
    monkeypatch.setattr(server, "_chromium_executable", broken)
    assert server._browser_check() == "unavailable"
