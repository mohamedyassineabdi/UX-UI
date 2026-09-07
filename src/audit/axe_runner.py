"""Pinned local axe-core execution; never loads code from a CDN."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.audit.measurement import measurement_metadata
from src.audit.result_semantics import stable_id


ROOT = Path(__file__).resolve().parents[2]
AXE_SCRIPT = ROOT / "node_modules" / "axe-core" / "axe.min.js"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


def axe_version() -> str | None:
    package = AXE_SCRIPT.parent / "package.json"
    try:
        return str(json.loads(package.read_text(encoding="utf-8")).get("version") or "") or None
    except (OSError, ValueError):
        return None


async def run_axe(page: Any, *, page_id: str) -> dict[str, Any]:
    version = axe_version()
    if not version:
        return {"measurement": "not_measured", **measurement_metadata("axe_core", "standards_automated", limitations=["Pinned axe-core package is unavailable in this deployment."]), "status": "unavailable", "pageId": page_id}
    try:
        await page.add_script_tag(path=str(AXE_SCRIPT))
        result = await page.evaluate("""async (tags) => await axe.run(document, { runOnly: { type: 'tag', values: tags } })""", AXE_TAGS)
        return {"measurement": "measured", **measurement_metadata("axe_core", "standards_automated", limitations=["Automated results do not prove full WCAG conformance."]), "status": "completed", "pageId": page_id, "toolVersion": version, "tags": AXE_TAGS, "raw": result}
    except Exception as exc:
        return {"measurement": "collection_failed", **measurement_metadata("axe_core", "standards_automated"), "status": "failed", "pageId": page_id, "toolVersion": version, "error": str(exc)[:300]}


def axe_findings(axe_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert definite axe violations to deduplicable Phase 2B evidence.

    Incomplete rules deliberately remain unknown review work and inapplicable
    rules never enter scoring/finding output.
    """
    if axe_result.get("status") != "completed" or axe_result.get("measurement") != "measured":
        return []
    page_id = str(axe_result.get("pageId") or "")
    raw = axe_result.get("raw") if isinstance(axe_result.get("raw"), dict) else {}
    version = str(axe_result.get("toolVersion") or "")
    findings: list[dict[str, Any]] = []
    impacts = {"critical": "high", "serious": "high", "moderate": "medium", "minor": "low"}
    for violation in raw.get("violations", []):
        if not isinstance(violation, dict) or not violation.get("id"):
            continue
        rule = str(violation["id"])
        for node in violation.get("nodes", []):
            if not isinstance(node, dict):
                continue
            target = " ".join(str(x) for x in node.get("target", []) if x) or "document"
            evidence_id = stable_id("evidence", "axe", page_id, rule, target)
            findings.append({
                "findingId": stable_id("finding", "axe", page_id, rule, target),
                "ruleId": f"axe:{rule}", "axeRuleId": rule,
                "title": str(violation.get("help") or rule), "target": target,
                "severity": impacts.get(str(violation.get("impact") or "").lower(), "medium"),
                "outcome": "fail", "applicability": "applicable", "measurement": "measured",
                "measurementMethod": "axe_core", "measurementClass": "standards_automated",
                "source": "axe-core", "sourceSheet": "Standards-based accessibility findings",
                "evidenceIds": [evidence_id], "impact": violation.get("impact"),
                "tags": list(violation.get("tags") or []), "tool": "axe-core", "toolVersion": version,
                "pageId": page_id, "failureSummary": str(node.get("failureSummary") or "")[:1200],
                "provenance": {"status": "verified", "pageRefs": [{"pageId": page_id}],
                               "evidence": [{"evidenceId": evidence_id, "target": target}]},
            })
    for incomplete in raw.get("incomplete", []):
        if isinstance(incomplete, dict) and incomplete.get("id"):
            findings.append({"findingId": stable_id("finding", "axe-incomplete", page_id, str(incomplete["id"])),
                             "ruleId": f"axe:{incomplete['id']}", "axeRuleId": str(incomplete["id"]),
                             "title": str(incomplete.get("help") or incomplete["id"]), "outcome": "unknown",
                             "applicability": "applicable", "measurement": "not_measured", "needsReview": True,
                             "measurementMethod": "axe_core", "measurementClass": "standards_automated",
                             "source": "axe-core", "sourceSheet": "Needs human review",
                             "provenance": {"status": "unresolved", "pageRefs": [{"pageId": page_id}]}})
    return findings
