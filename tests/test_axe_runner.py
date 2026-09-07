import asyncio
from pathlib import Path

import pytest

from src.audit.axe_runner import AXE_TAGS, axe_findings, axe_version, run_axe
from src.gtm_audit.scoring import deduplicate_findings


def test_axe_runner_uses_pinned_local_tooling_and_wcag_tags():
    assert "wcag22aa" in AXE_TAGS
    # The test environment may deliberately omit node_modules; capability then
    # reports not_measured rather than pretending a standards result exists.
    assert axe_version() is None or axe_version().count(".") >= 2


def test_axe_fixture_executes_pinned_bundle_and_converts_evidence():
    pytest.importorskip("playwright.async_api")
    if not axe_version():
        pytest.skip("Pinned axe-core is unavailable")

    async def exercise():
        from playwright.async_api import async_playwright
        fixture = (Path(__file__).parent / "fixtures" / "audit_site" / "index.html").read_text(encoding="utf-8")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()
                page = await context.new_page()
                await page.set_content(fixture)
                return await run_axe(page, page_id="fixture-page")
            finally:
                await browser.close()

    result = asyncio.run(exercise())
    assert result["status"] == "completed"
    assert result["toolVersion"] == "4.11.1"
    violations = {item["id"]: item for item in result["raw"]["violations"]}
    assert "button-name" in violations and "label" in violations
    assert any("#fixture-unnamed-button" in target for node in violations["button-name"]["nodes"] for target in node["target"])
    assert any("#fixture-unlabeled-input" in target for node in violations["label"]["nodes"] for target in node["target"])
    findings = axe_findings(result)
    button = next(item for item in findings if item.get("axeRuleId") == "button-name")
    assert button["measurementClass"] == "standards_automated"
    assert button["tool"] == "axe-core" and button["evidenceIds"]


def test_axe_incomplete_is_unknown_and_standards_evidence_is_deduplication_primary():
    result = {"status": "completed", "measurement": "measured", "pageId": "p", "toolVersion": "4.11.1", "raw": {
        "violations": [{"id": "button-name", "help": "Buttons must have discernible text", "impact": "critical", "tags": ["wcag2a"], "nodes": [{"target": ["#save"], "failureSummary": "missing name"}]}],
        "incomplete": [{"id": "color-contrast", "help": "Contrast needs review"}],
    }}
    findings = axe_findings(result)
    assert next(item for item in findings if item["axeRuleId"] == "color-contrast")["outcome"] == "unknown"
    axe = next(item for item in findings if item["axeRuleId"] == "button-name")
    duplicate = {**axe, "findingId": "zzz", "source": "custom", "sourceSheet": "Custom accessibility observations"}
    merged = deduplicate_findings([duplicate, axe])
    assert len(merged) == 1 and merged[0]["source"] == "axe-core"
