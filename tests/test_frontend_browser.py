"""Rendered frontend contracts against the real authenticated local API.

Run npm run build first. Audit execution and external publication are replaced
with deterministic fixtures; authentication, review transitions and storage run
through the server. Screenshots are optional via UX_UI_QA_DIR.
"""
import json
import os
import base64
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from src.ui import server
from test_server_security import api_server, request


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def ui(browser, api_server, monkeypatch, tmp_path):
    # Keep the real artifact route layout in an isolated temporary workspace.
    monkeypatch.setattr(server, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(server, "AUDITS_DIR", tmp_path / "shared" / "audits")
    monkeypatch.setattr(server, "GENERATED_DIR", tmp_path / "shared" / "generated")
    monkeypatch.setattr(server, "_detailed_workbook_template_available", lambda: False)
    monkeypatch.setattr(server, "_publish_job_report", lambda *_args: "https://example.test/reviewed")
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light", reduced_motion="reduce")
    context.add_init_script("sessionStorage.setItem('internalPortalToken', 'token-a')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" and not message.text.startswith("Failed to load resource:") else None)
    page.goto(f"http://127.0.0.1:{api_server.server_port}")
    expect(page.get_by_role("heading", name="New audit", exact=True)).to_be_visible()
    yield page, api_server, errors
    assert not errors, errors
    context.close()


def screenshot(page, name):
    directory = os.environ.get("UX_UI_QA_DIR")
    if directory:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        previous_scroll = page.evaluate("scrollY")
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(target / f"{name}.png"), full_page=True)
        page.evaluate("y => scrollTo(0, y)", previous_scroll)


def axe(page):
    page.add_script_tag(path=str(ROOT / "node_modules" / "axe-core" / "axe.min.js"))
    violations = page.evaluate("""async () => (await axe.run(document, {
        runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}
    })).violations.map(item => ({id: item.id, nodes: item.nodes.map(node => node.target)}))""")
    assert violations == []


def tab_to(page, locator):
    for _ in range(80):
        if locator.evaluate("element => element === document.activeElement"):
            return
        page.keyboard.press("Tab")
    raise AssertionError("Control could not be reached with Tab")


def start(page, keyboard=False):
    if keyboard:
        tab_to(page, page.get_by_label("Website URL"))
        page.keyboard.insert_text("https://example.com")
        tab_to(page, page.get_by_role("button", name="Start audit", exact=True))
    else:
        page.get_by_label("Website URL").fill("https://example.com")
    with page.expect_response(lambda response: response.url.endswith("/api/audits") and response.request.method == "POST") as created:
        if keyboard:
            page.keyboard.press("Enter")
        else:
            page.get_by_role("button", name="Start audit", exact=True).click()
    job = created.value.json()
    expect(page.get_by_role("heading", name="Your audit is in the queue.")).to_be_visible()
    return job


def complete(page, wait_for_review=True, keyboard=False, count=2, transform=None):
    job = start(page, keyboard=keyboard)
    workspace = server.AuditWorkspace(job["id"], server.AUDITS_DIR)
    workspace.gtm_audit.parent.mkdir(parents=True, exist_ok=True)
    finding = {
        "deduplicationId": "defect_" + "a" * 130,
        "title": "Primary action has insufficient contrast",
        "severity": "high", "outcome": "fail",
        "evidence": ["The primary action label has a measured contrast ratio of 2.8:1."],
        "explanation": "The action is difficult to distinguish on its background.",
        "whyItMatters": "People with low vision may miss the next step.",
        "recommendation": "Increase label contrast and retest the control.",
        "evidenceIds": ["evidence_1"],
    }
    capture = workspace.screenshots / "checkout.png"
    capture.parent.mkdir(parents=True, exist_ok=True)
    evidence_page = page.context.new_page()
    evidence_page.set_viewport_size({"width": 920, "height": 400})
    evidence_page.set_content("""<html lang="en"><body style="font:18px system-ui;margin:0;background:#f3f5f7;color:#20252c"><div style="padding:28px 48px;border-bottom:1px solid #ddd;background:white">NORTH &nbsp; / &nbsp; Checkout</div><main style="margin:32px auto;width:560px;background:white;padding:24px 36px;border-radius:12px"><h2 style="margin:0">Complete your order</h2><p>Review your delivery details before continuing.</p><p>Studio notebook &nbsp; ? 1 &nbsp; ? &nbsp; $24.00</p><button style="padding:14px 28px;border:2px dashed #bd4655;background:#bacafa;color:white;border-radius:8px">Continue to payment</button></main></body></html>""")
    evidence_page.screenshot(path=str(capture))
    evidence_page.close()
    finding.update({"axisId": "trust_accessibility", "axisName": "Accessibility", "pageUrl": "https://example.com/checkout", "screenshotPath": str(capture), "evidenceBundle": {"source": "axe-core", "criterion": "1.4.3", "target": "button.checkout", "raw": {"contrastRatio": 2.8, "expectedRatio": 4.5}}})
    second = {"findingId": "finding_2", "title": "Form feedback needs a clear recovery path", "axisId": "content_microcopy", "axisName": "Content Clarity & Guidance", "severity": "medium", "evidence": "The error message does not explain how to continue."}
    findings = [finding, second][:count]
    for index in range(2, count):
        findings.append({"findingId": f"finding_{index + 1}", "title": f"Checkout observation {index + 1}", "severity": "low" if index % 2 else "high", "axisName": "Accessibility", "evidence": "A captured interface control needs review."})
    names = [("task_execution", "Task Effectiveness & Interaction", 40, .60), ("flow_architecture", "Information Architecture & Navigation", 74, 1), ("trust_accessibility", "Accessibility", 52, .85), ("ui_consistency", "Visual Hierarchy & Interface Consistency", 86, .40), ("content_microcopy", "Content Clarity & Guidance", 68, .75)]
    machine = {"axisMethodologyVersion": 2, "deduplicatedFindings": findings, "executiveSummary": {"overallScore": 68, "overallCoverage": .72, "summary": "The checkout needs clearer feedback and more legible actions. Navigation is consistent across the captured pages."}, "axes": [{"id": key, "name": name, "score": score, "scored": True, "confidence": .84, "signals": {"measurementCoverage": coverage, "measuredRules": 6, "applicableRules": 10, "unknownRules": 4}} for key, name, score, coverage in names], "coverage": {"summary": {"discovered": 8, "selected": 5, "completed": 4, "failed": 1, "excluded": 3, "coverageRatio": .8, "coverageStatus": "partial"}}, "scannedPages": [{"title": "Checkout", "page_url": "https://example.com/checkout"}]}
    if transform:
        transform(machine)
    workspace.gtm_audit.write_text(json.dumps(machine), encoding="utf-8")
    report = workspace.publication / "audits" / job["id"] / "index.html"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("<!doctype html><html lang='en'><head><title>Fixture report</title><link rel='stylesheet' href='./styles.css'></head><body><h1>Protected audit report</h1><p>Evidence available.</p><img src='./evidence.png' alt='Captured evidence'><script src='./app.js'></script></body></html>", encoding="utf-8")
    (report.parent / "styles.css").write_text("h1 { color: rgb(30, 60, 90); }", encoding="utf-8")
    (report.parent / "app.js").write_text("document.querySelector('p').textContent = 'Report interaction ready';", encoding="utf-8")
    (report.parent / "evidence.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII="))
    server.JOB_STORE.update(job["id"], status="running")
    server.JOB_STORE.update(job["id"], status="completed", stage="Ready for local review", resultUrl=f"/audits/{job['id']}/")
    expect(page.get_by_role("heading", name="Audit overview")).to_be_visible(timeout=10000)
    if wait_for_review:
        control = page.get_by_role("tab", name="Review", exact=True)
        if keyboard:
            tab_to(page, page.get_by_role("tab", name="Overview", exact=True))
            page.keyboard.press("ArrowLeft")
        else:
            control.click()
        expect(page.get_by_label("Review decision")).to_be_visible()
    return job, finding


@pytest.mark.parametrize("width", [375, 768, 1024, 1440])
def test_setup_responsive_keyboard_and_contrast(ui, width):
    page, _, _ = ui
    page.set_viewport_size({"width": width, "height": 1000})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.get_by_label("Audit mode").count() == 0
    page.get_by_role("radio", name="Website Explore a live website").focus()
    page.keyboard.press("ArrowRight")
    expect(page.get_by_role("radio", name="Screenshots Review captured screens")).to_be_checked()
    page.keyboard.press("ArrowLeft")
    expect(page.get_by_label("Website URL")).to_be_visible()
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    axe(page)
    screenshot(page, f"setup-{width}-light")
    page.reload()


def test_source_configuration_upload_removal_and_discovery(ui, monkeypatch):
    page, _, _ = ui
    page.get_by_role("radio", name="Screenshots Review captured screens").check()
    page.get_by_label("Choose screenshots").set_input_files([{"name": "checkout.png", "mimeType": "image/png", "buffer": b"fixture"}])
    expect(page.get_by_text("checkout.png", exact=True)).to_be_visible()
    page.get_by_role("button", name="Remove checkout.png").click()
    expect(page.get_by_text("checkout.png", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Start audit", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Couldn’t start this audit")
    screenshot(page, "screenshots-empty-validation")
    monkeypatch.setattr(server, "_mobile_discovery_payload", lambda: {"selectedDevice": {"deviceName": "Test Android", "state": "device"}, "defaults": {"deviceName": "Test Android", "udid": "test-device"}, "currentApp": {"appPackage": "com.example.app", "appActivity": ".MainActivity"}, "launchableApps": [], "warnings": []})
    page.get_by_role("radio", name="Mobile App Explore an Android app").check()
    page.get_by_role("button", name="Discover device & apps").click()
    expect(page.get_by_label("App package", exact=True)).to_have_value("com.example.app")
    expect(page.get_by_label("Launch activity", exact=True)).to_have_value(".MainActivity")
    screenshot(page, "mobile-discovery")
    page.get_by_role("radio", name="Figma Review a design file").check()
    expect(page.get_by_label("Figma file URL")).to_be_visible()
    axe(page)
    screenshot(page, "figma-setup")


@pytest.mark.parametrize("status", ["queued", "running", "failed", "cancelled", "interrupted"])
def test_job_states_terminal_polling_and_long_errors(ui, status):
    page, _, _ = ui
    job = start(page)
    if status != "queued":
        server.JOB_STORE.update(job["id"], status="running", stage="Collecting representative page evidence")
        if status != "running":
            server.JOB_STORE.update(job["id"], status=status, error="Runtime unavailable. " + "TechnicalDetail" * 80)
        expect(page.locator(f".status-{status}").first).to_be_visible(timeout=10000)
    screenshot(page, f"job-{status}-1440")
    page.set_viewport_size({"width": 375, "height": 1000})
    if status in {"failed", "cancelled", "interrupted"}:
        assert page.get_by_role("button", name="Cancel audit", exact=True).count() == 0
        calls = []
        page.on("request", lambda req: calls.append(req.url) if req.url.endswith(job["id"]) else None)
        page.wait_for_timeout(1800)
        assert not calls
        page.get_by_text("Details", exact=True).click()
    else:
        assert page.get_by_role("progressbar").get_attribute("aria-valuenow") is None
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    axe(page)
    screenshot(page, f"job-{status}-375")


def test_cancel_request_and_new_audit_navigation(ui):
    page, _, _ = ui
    start(page)
    page.get_by_role("button", name="Cancel audit", exact=True).click()
    expect(page.get_by_role("heading", name="This audit was cancelled.")).to_be_visible()
    page.get_by_role("button", name="Start another audit").click()
    expect(page.get_by_label("Website URL")).to_be_visible()


def test_running_cancellation_keeps_polling_until_terminal(ui):
    page, _, _ = ui
    job = start(page)
    server.JOB_STORE.update(job["id"], status="running", stage="Collecting evidence")
    expect(page.locator(".status-running")).to_be_visible(timeout=10000)
    page.get_by_role("button", name="Cancel audit", exact=True).click()
    expect(page.get_by_role("button", name="Cancelling…")).to_be_disabled()
    server.JOB_STORE.update(job["id"], status="cancelled")
    expect(page.get_by_role("heading", name="This audit was cancelled.")).to_be_visible(timeout=10000)


def test_review_save_validate_approve_publish_and_protected_report(ui):
    page, instance, _ = ui
    job, finding = complete(page)
    page.get_by_label("Review decision").select_option("confirmed")
    page.get_by_label("Review note", exact=True).fill("Verified against the captured evidence.")
    page.get_by_text("Recommendation & executive priorities", exact=True).click()
    page.get_by_label("Reviewed recommendation", exact=True).fill("Use a darker label and verify its contrast.")
    page.get_by_label("Priority override").select_option("critical")
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_role("button", name="Validate revision")).to_be_enabled()
    review = json.loads(request(instance, "GET", f"/api/audits/{job['id']}/review", token="token-a")[2])
    assert review["revisions"][0]["changes"][finding["deduplicationId"]]["priorityOverride"] == "critical"
    page.get_by_role("button", name="Validate revision").click()
    expect(page.get_by_role("button", name="Publish reviewed report")).to_be_enabled()
    page.get_by_role("button", name="Approve revision").click()
    expect(page.locator(".review-actionbar .status-approved")).to_be_visible()
    page.get_by_role("button", name="Publish reviewed report").click()
    expect(page.get_by_role("link", name="Open published report")).to_be_visible()
    screenshot(page, "review-published-1440-light")
    with page.expect_popup() as popup:
        page.get_by_role("button", name="Open report", exact=True).click()
    report_tab = popup.value
    expect(report_tab.frame_locator("iframe").get_by_role("heading", name="Protected audit report")).to_be_visible(timeout=10000)
    expect(report_tab.frame_locator("iframe").get_by_text("Report interaction ready")).to_be_visible()
    expect(report_tab.frame_locator("iframe").get_by_role("heading")).to_have_css("color", "rgb(30, 60, 90)")
    assert report_tab.frame_locator("iframe").get_by_alt_text("Captured evidence").evaluate("image => image.naturalWidth") == 1
    assert report_tab.evaluate("window.opener === null")
    report_tab.close()
    axe(page)
    for width in [375, 768, 1024, 1440]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        axe(page)
        screenshot(page, f"review-{width}-light")


def test_review_conflict_preserves_draft_and_blocks_transitions(ui):
    page, instance, _ = ui
    job, finding = complete(page)
    page.get_by_label("Review note", exact=True).fill("My unsaved draft")
    request(instance, "POST", f"/api/audits/{job['id']}/revisions", token="token-a", body={"findingChanges": {finding["deduplicationId"]: {"reviewNote": "Another reviewer's edit"}}, "expectedRevisionId": None})
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("This review was changed in another session. Refresh before saving again.")).to_be_visible()
    expect(page.get_by_label("Review note", exact=True)).to_have_value("My unsaved draft")
    page.get_by_role("button", name="Refresh latest revision").click()
    expect(page.get_by_role("button", name="Use latest revision", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Save revision", exact=True)).to_be_disabled()
    screenshot(page, "review-conflict")
    page.get_by_role("button", name="Use my draft as next revision").click()
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("All changes saved", exact=True)).to_be_visible()
    review = json.loads(request(instance, "GET", f"/api/audits/{job['id']}/review", token="token-a")[2])
    assert len(review["revisions"]) == 2
    assert review["revisions"][-1]["changes"][finding["deduplicationId"]]["reviewNote"] == "My unsaved draft"


def test_suppression_validation_and_draft_survives_navigation(ui):
    page, _, _ = ui
    complete(page)
    page.get_by_text("Recommendation & executive priorities", exact=True).click()
    page.get_by_label("Suppress from executive priorities").check()
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("Add a suppression reason for every suppressed finding.")).to_be_visible()
    page.get_by_label("Suppression reason", exact=True).fill("Confirmed duplicate")
    page.get_by_role("navigation", name="Workspace").get_by_role("button", name="New audit").click()
    page.get_by_role("button", name="Current audit").click()
    expect(page.get_by_label("Suppression reason", exact=True)).to_have_value("Confirmed duplicate")
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_role("button", name="Validate revision")).to_be_enabled()


def test_capability_errors_and_detailed_mode(ui, monkeypatch):
    page, _, _ = ui
    monkeypatch.setattr(server, "_detailed_workbook_template_available", lambda: True)
    page.reload()
    page.get_by_text("Advanced · audit mode").click()
    expect(page.get_by_label("Audit mode")).to_be_visible()
    page.get_by_label("Audit mode").select_option("detailed")
    job = start(page)
    assert job["mode"] == "detailed"


def test_capability_network_failure_and_retry(ui):
    page, _, _ = ui
    page.route("**/api/capabilities", lambda route: route.abort())
    page.reload()
    expect(page.get_by_text("Advanced audit modes are unavailable")).to_be_visible()
    page.get_by_text("Details", exact=True).click()
    expect(page.locator(".alert-warning")).to_contain_text("Unable to reach the audit server")
    screenshot(page, "network-error")
    page.unroute("**/api/capabilities")
    page.get_by_role("button", name="Try again").click()
    expect(page.locator(".alert-warning")).to_have_count(0)


def test_signed_out_blocks_start(ui):
    page, _, _ = ui
    page.route("**/api/capabilities", lambda route: route.fulfill(status=401, json={"error": "Authentication required."}))
    page.reload()
    expect(page.get_by_text("Sign in to start an audit")).to_be_visible()
    expect(page.get_by_role("button", name="Start audit")).to_be_disabled()
    page.unroute("**/api/capabilities")
    page.get_by_role("button", name="I’ve signed in, check again").click()
    expect(page.get_by_role("button", name="Start audit")).to_be_enabled()


def test_review_loading_and_publishing_states(ui):
    page, _, _ = ui
    pending = []
    page.route("**/review", lambda route: pending.append(route))
    complete(page, wait_for_review=False)
    page.get_by_role("tab", name="Review", exact=True).click()
    expect(page.get_by_text("Loading review…", exact=True)).to_be_visible()
    screenshot(page, "review-loading")
    pending.pop().continue_()
    page.unroute("**/review")
    expect(page.get_by_label("Review decision")).to_be_visible()
    screenshot(page, "review-clean")
    page.get_by_label("Review decision").select_option("accepted")
    page.get_by_role("button", name="Save revision", exact=True).click()
    page.get_by_role("button", name="Validate revision").click()
    page.route("**/publish", lambda route: pending.append(route))
    page.get_by_role("button", name="Publish reviewed report").click()
    expect(page.get_by_role("button", name="Publishing…")).to_be_disabled()
    expect(page.get_by_label("Review decision")).to_be_disabled()
    screenshot(page, "review-publishing")
    pending.pop().continue_()
    expect(page.get_by_role("link", name="Open published report")).to_be_visible()


def test_server_validation_keeps_draft_and_blocks_next_action(ui):
    page, _, _ = ui
    complete(page)
    page.get_by_label("Review note", exact=True).fill("Keep this text")
    page.route("**/revisions", lambda route: route.fulfill(status=400, json={"error": "Machine-owned fields cannot be revised."}))
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("Couldn’t save your changes", exact=True)).to_be_visible()
    expect(page.get_by_label("Review note", exact=True)).to_have_value("Keep this text")
    assert page.get_by_role("button", name="Validate revision").count() == 0
    screenshot(page, "review-validation-error")


def test_dismissed_unsaved_confirmation_never_creates_a_job(ui):
    page, _, _ = ui
    complete(page)
    page.get_by_label("Review note", exact=True).fill("Keep this draft")
    page.get_by_role("navigation", name="Workspace").get_by_role("button", name="New audit").click()
    posts = []
    page.on("request", lambda req: posts.append(req.url) if req.method == "POST" else None)
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Start audit", exact=True).click()
    assert not posts
    page.get_by_role("button", name="Current audit").click()
    expect(page.get_by_label("Review note", exact=True)).to_have_value("Keep this draft")


def test_keyboard_only_creation_and_review_actions(ui):
    page, _, _ = ui
    complete(page, keyboard=True)
    tab_to(page, page.get_by_label("Review note", exact=True))
    page.keyboard.insert_text("Keyboard-reviewed finding")
    for action in ["Save revision", "Validate revision", "Approve revision", "Publish reviewed report"]:
        control = page.get_by_role("button", name=action, exact=True)
        expect(control).to_be_enabled()
        tab_to(page, control)
        assert control.evaluate("element => getComputedStyle(element).outlineStyle") != "none"
        screenshot(page, "keyboard-focus-" + action.split()[0].lower())
        page.keyboard.press("Enter")
    expect(page.get_by_role("link", name="Open published report")).to_be_visible()


def test_expired_session_is_explicit(ui):
    page, _, _ = ui
    page.evaluate("sessionStorage.removeItem('internalPortalToken')")
    # Remove the fixture's init script by opening a fresh context-free request
    # through the existing page instead of reloading it.
    page.route("**/api/audits", lambda route: route.continue_(headers={key: value for key, value in route.request.headers.items() if key != "authorization"}))
    page.get_by_label("Website URL").fill("https://example.com")
    page.get_by_role("button", name="Start audit", exact=True).click()
    expect(page.get_by_text("Your session needs attention", exact=True)).to_be_visible()
    expect(page.get_by_role("alert")).to_contain_text("Sign in through your portal")


def test_review_action_error_ownership_and_success_clear_stale_error(ui):
    page, _, _ = ui
    complete(page)
    page.get_by_label("Review note", exact=True).fill("Evidence checked")
    page.get_by_role("button", name="Save revision", exact=True).click()
    page.route("**/validate", lambda route: route.fulfill(status=500, json={"error": "Temporary validation failure"}))
    page.get_by_role("button", name="Validate revision").click()
    expect(page.get_by_text("Couldn’t validate this revision", exact=True)).to_be_visible()
    screenshot(page, "review-validation-error")
    page.unroute("**/validate")
    page.get_by_role("button", name="Validate revision").click()
    expect(page.locator(".review-actionbar .status-validated")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
    screenshot(page, "review-validated")
    page.route("**/approve", lambda route: route.fulfill(status=500, json={"error": "Approval unavailable"}))
    page.get_by_role("button", name="Approve revision").click()
    expect(page.get_by_text("Couldn’t approve this revision", exact=True)).to_be_visible()
    expect(page.locator(".review-actionbar .status-validated")).to_be_visible()
    # A validated revision can still publish after optional approval fails.
    page.route("**/publish", lambda route: route.fulfill(status=503, json={"error": "Publication unavailable"}))
    page.get_by_role("button", name="Publish reviewed report").click()
    expect(page.get_by_text("Couldn’t publish the reviewed report", exact=True)).to_be_visible()
    expect(page.get_by_text("Couldn’t approve this revision", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Dismiss error").click()
    expect(page.get_by_role("alert")).to_have_count(0)
    page.get_by_role("button", name="Publish reviewed report").click()
    expect(page.get_by_text("Couldn’t publish the reviewed report", exact=True)).to_be_visible()
    page.unroute("**/publish")
    page.get_by_role("button", name="Publish reviewed report").click()
    expect(page.get_by_role("link", name="Open published report")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
    # Changing the relevant draft clears an error against its previous state.
    page.get_by_role("button", name="Approve revision").click()
    expect(page.get_by_role("alert")).to_be_visible()
    page.get_by_label("Review note", exact=True).fill("Changed judgment")
    expect(page.get_by_role("alert")).to_have_count(0)


@pytest.mark.parametrize("count", [1, 15, 100])
def test_finding_scale_filters_evidence_and_mobile_drill_in(ui, count):
    page, _, _ = ui
    complete(page, wait_for_review=False, count=count)
    page.get_by_role("tab", name="Findings", exact=False).click()
    expect(page.locator(".finding-item")).to_have_count(min(count, 25))
    if count == 1:
        expect(page.get_by_label("Find a finding")).to_have_count(0)
        expect(page.get_by_label("Severity", exact=True)).to_have_count(0)
    else:
        page.get_by_label("Find a finding").fill("recovery")
        expect(page.locator(".finding-item")).to_have_count(1)
        page.locator(".finding-item").click()
        expect(page.get_by_role("heading", name="Form feedback needs a clear recovery path")).to_be_visible()
        page.get_by_role("tab", name="Overview", exact=True).click()
        page.get_by_role("tab", name="Findings", exact=False).click()
        expect(page.get_by_label("Find a finding")).to_have_value("recovery")
        page.get_by_role("button", name="Clear filters").click()
        page.get_by_label("Severity", exact=True).select_option("high")
        assert page.locator(".finding-item").count() >= 1
        assert page.locator(".finding-item .severity-label").all_text_contents() == ["high"] * page.locator(".finding-item").count()
        page.get_by_role("button", name="Clear filters").click()
        page.get_by_label("UX dimension").select_option("Content Clarity & Guidance")
        expect(page.locator(".finding-item")).to_have_count(1)
        page.get_by_role("button", name="Clear filters").click()
        if count == 100:
            page.get_by_role("button", name="Show next 25 findings").click()
            expect(page.locator(".finding-item")).to_have_count(50)
    page.locator(".finding-item").first.click()
    preview = page.get_by_role("img", name="Captured interface", exact=False)
    expect(preview).to_be_visible()
    assert preview.evaluate("image => image.naturalWidth") == 920
    assert preview.get_attribute("src").startswith("blob:")
    page.get_by_text("Evidence provenance & check details", exact=True).click()
    expect(page.get_by_text("button.checkout", exact=True)).to_be_visible()
    page.locator(".finding-detail").evaluate("element => element.scrollTop = 0")
    screenshot(page, f"findings-{count}-1440")
    page.get_by_role("tab", name="Review", exact=True).click()
    page.get_by_label("Review decision").select_option("confirmed")
    if count > 1:
        page.get_by_label("Review state").select_option("confirmed")
        expect(page.locator(".finding-item")).to_have_count(1)
    screenshot(page, f"review-dirty-{count}")
    page.set_viewport_size({"width": 375, "height": 1000})
    expect(page.get_by_label("Review decision")).to_be_visible()
    page.get_by_role("button", name="Back to findings", exact=False).click()
    expect(page.locator(".finding-navigation")).to_be_visible()
    selected = page.locator(".finding-item[aria-pressed=true]")
    expect(selected).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator(".finding-detail-heading h2")).to_be_focused()
    page.get_by_label("Review note", exact=True).fill("Mobile review")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    axe(page)
    screenshot(page, f"review-mobile-{count}")


def test_overview_score_coverage_responsive_and_unknown_measurements(ui):
    page, _, _ = ui
    job, _ = complete(page, wait_for_review=False, count=15)
    expect(page.get_by_text("40 / 100", exact=True)).to_be_visible()
    expect(page.get_by_text("60%", exact=True)).to_be_visible()
    expect(page.get_by_text("Pages collected", exact=True)).to_be_visible()
    for width in [375, 768, 1024, 1280, 1440, 1728]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        axe(page)
        screenshot(page, f"overview-{width}-light")


def test_missing_zero_and_model_scores_are_not_conflated(ui):
    page, _, _ = ui
    def transform(machine):
        machine["axes"][0].update(score=0)
        machine["axes"][1].update(score=None, scored=False, scoreReason="Collection did not measure these rules.")
        machine["axes"][1]["signals"].update(measurementCoverage=0, visionScore=82)
    complete(page, wait_for_review=False, transform=transform)
    rows = page.locator(".axis-scorecard details")
    expect(rows.nth(0)).to_contain_text("0 / 100")
    expect(rows.nth(1)).to_contain_text("Not measured")
    expect(rows.nth(1)).to_contain_text("0%")
    rows.nth(1).locator("summary").click()
    expect(rows.nth(1)).to_contain_text("Model visual assessment: 82 / 100")
    expect(rows.nth(1)).to_contain_text("Collection did not measure these rules.")
    screenshot(page, "overview-missing-measurement")


def test_skip_link_light_theme_text_zoom_and_keyboard_tabs(ui):
    page, _, _ = ui
    page.emulate_media(color_scheme="dark", reduced_motion="reduce")
    page.reload()
    page.keyboard.press("Tab")
    skip = page.get_by_role("link", name="Skip to content")
    expect(skip).to_be_focused()
    assert skip.bounding_box()["y"] >= 0
    page.keyboard.press("Enter")
    expect(page.locator("main")).to_be_focused()
    expect(skip).to_have_css("clip-path", "inset(50%)")
    complete(page, wait_for_review=False)
    tab = page.get_by_role("tab", name="Overview", exact=True)
    tab.focus()
    page.keyboard.press("ArrowRight")
    expect(page.get_by_role("tab", name="Findings", exact=False)).to_be_focused()
    page.keyboard.press("End")
    expect(page.get_by_role("tab", name="Review", exact=True)).to_be_focused()
    page.keyboard.press("Home")
    expect(tab).to_be_focused()
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    page.set_viewport_size({"width": 375, "height": 1000})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    screenshot(page, "overview-text-200percent")



def test_successful_mutation_survives_failed_refresh(ui):
    page, instance, _ = ui
    job, _ = complete(page)
    page.get_by_label("Review note", exact=True).fill("Save this authoritative result")
    page.route("**/review", lambda route: route.fulfill(status=503, json={"error": "Read replica unavailable"}))
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("Action completed; revision refresh is unavailable", exact=True)).to_be_visible()
    expect(page.get_by_text("All changes saved", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Validate revision")).to_be_enabled()
    review = json.loads(request(instance, "GET", f"/api/audits/{job['id']}/review", token="token-a")[2])
    assert review["reviewStatus"] == "in_review"
    page.unroute("**/review")
    page.get_by_role("button", name="Validate revision").click()
    expect(page.locator(".review-actionbar .status-validated")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


def test_post_save_refresh_detects_another_revision_without_overwriting_draft(ui):
    page, instance, _ = ui
    job, finding = complete(page)
    page.get_by_label("Review note", exact=True).fill("My saved judgment")
    def replace_revision(route):
        current = json.loads(request(instance, "GET", f"/api/audits/{job['id']}/review", token="token-a")[2])
        result = request(instance, "POST", f"/api/audits/{job['id']}/revisions", token="token-a",
                         body={"findingChanges": {finding["deduplicationId"]: {"reviewNote": "Concurrent judgment"}},
                               "expectedRevisionId": current["currentRevision"]})
        assert result[0] == 201
        route.continue_()
    page.route("**/review", replace_revision, times=1)
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("This review was changed in another session. Refresh before saving again.")).to_be_visible()
    expect(page.get_by_label("Review note", exact=True)).to_have_value("My saved judgment")
    expect(page.get_by_role("button", name="Validate revision")).to_be_disabled()
    page.get_by_role("button", name="Use latest revision", exact=True).click()
    expect(page.get_by_label("Review note", exact=True)).to_have_value("Concurrent judgment")
    expect(page.get_by_role("button", name="Validate revision")).to_be_enabled()


def test_completed_overview_opens_local_interactive_report_and_deploys_saved_revision(ui):
    page, instance, _ = ui
    job, _ = complete(page, wait_for_review=False)
    expect(page.get_by_role("tab")).to_have_count(0)
    expect(page.get_by_text("Human review", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Open artifacts", exact=True)).to_have_count(0)
    route = f"http://127.0.0.1:{instance.server_port}/report/{job['id']}"
    direct = page.request.get(route)
    assert direct.status == 200 and "text/html" in direct.headers["content-type"] and "root" in direct.text()
    missing = page.request.get(f"http://127.0.0.1:{instance.server_port}/report/not-a-real-audit")
    assert missing.status == 404 and "Audit job not found" in missing.text()
    screenshot(page, "workflow-completed-overview")
    page.get_by_role("link", name="Open report", exact=True).click()
    expect(page).to_have_url(re.compile(f"/report/{job['id']}$"))
    expect(page.get_by_text("Local report", exact=True)).to_be_visible()
    screenshot(page, "workflow-local-report")
    page.go_back()
    expect(page.get_by_role("link", name="Open report", exact=True)).to_be_visible()
    page.go_forward()
    expect(page.get_by_text("Local report", exact=True)).to_be_visible()
    page.get_by_role("button", name="Review / Edit", exact=True).click()
    page.get_by_label("Review decision").select_option("confirmed")
    page.get_by_label("Review note", exact=True).fill("Saved in the local interactive report")
    page.locator(".finding-detail").evaluate("element => element.scrollTop = element.scrollHeight")
    screenshot(page, "workflow-report-edit-mode")
    page.get_by_role("button", name="Save edits", exact=True).click()
    expect(page.get_by_text("Saved locally", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_role("button", name="Review / Edit", exact=True)).to_be_visible()
    page.get_by_role("button", name="Review / Edit", exact=True).click()
    expect(page.get_by_label("Review note", exact=True)).to_have_value("Saved in the local interactive report")
    expect(page.get_by_text("Saved locally", exact=True)).to_be_visible()
    deploy = page.locator(".report-actionbar").get_by_role("button", name="Deploy report", exact=True)
    expect(deploy).to_be_enabled()
    deploy.click()
    expect(page.get_by_text("Report deployed", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Open deployed report", exact=True)).to_have_attribute("href", "https://example.test/reviewed")
    screenshot(page, "workflow-deployed")


def test_interactive_report_blocks_unsaved_deployment_and_keeps_local_revision_on_failure(ui):
    page, instance, _ = ui
    job, _ = complete(page, wait_for_review=False)
    page.goto(f"http://127.0.0.1:{instance.server_port}/report/{job['id']}")
    expect(page.get_by_role("button", name="Review / Edit", exact=True)).to_be_visible()
    page.get_by_role("button", name="Review / Edit", exact=True).click()
    page.get_by_label("Review note", exact=True).fill("Keep this local revision")
    deploy = page.locator(".report-actionbar").get_by_role("button", name="Deploy report", exact=True)
    expect(deploy).to_be_disabled()
    page.get_by_role("button", name="Save edits", exact=True).click()
    expect(page.get_by_text("Saved locally", exact=True)).to_be_visible()
    page.route("**/publish", lambda route: route.fulfill(status=502, json={"error": "Vercel unavailable"}))
    deploy.click()
    expect(page.get_by_text("Couldn’t publish the reviewed report", exact=True)).to_be_visible()
    expect(page.get_by_text("Saved locally", exact=True)).to_be_visible()

