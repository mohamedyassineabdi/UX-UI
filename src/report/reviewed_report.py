"""Small immutable review-report context and safe HTML renderer for Phase 4A."""
from __future__ import annotations

from typing import Any



def reviewed_report_context(*, audit_id: str, machine: dict[str, Any], revision: dict[str, Any] | None) -> dict[str, Any]:
    changes = (revision or {}).get("changes") if isinstance((revision or {}).get("changes"), dict) else {}
    findings = machine.get("allFindings") or machine.get("findings") or machine.get("deduplicatedFindings") or [point for axis in machine.get("axes", []) if isinstance(axis, dict) for point in axis.get("painPoints", [])]
    priorities = machine.get("priorities") or machine.get("executiveSummary", {}).get("topPriorities") or []
    complete = []
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, dict): continue
        item = dict(finding); item["review"] = changes.get(str(finding.get("findingId") or finding.get("id") or finding.get("deduplicationId") or ""), {})
        complete.append(item)
    def priority_review(item: dict[str, Any]) -> dict[str, Any]:
        identity = str(item.get("findingId") or item.get("id") or item.get("deduplicationId") or "")
        if identity:
            return changes.get(identity, {})
        # GTM priorities copy source findings with axis metadata but omit the
        # deduplication ID. Resolve only an exact, unambiguous record match.
        fields = {key: value for key, value in item.items() if key not in {"axisId", "axisName", "axisScore"}}
        matches = [finding for finding in complete if fields and all(finding.get(key) == value for key, value in fields.items())]
        return matches[0]["review"] if len(matches) == 1 else {}
    active_priorities = [item for item in priorities if not priority_review(item).get("suppressed")]
    summary = machine.get("summary") if isinstance(machine.get("summary"), dict) else {}
    executive = machine.get("executiveSummary") if isinstance(machine.get("executiveSummary"), dict) else {}
    return {"auditId": audit_id, "revisionId": (revision or {}).get("revisionId"), "reviewStatus": (revision or {}).get("reviewStatus", "unreviewed"),
            "reviewer": {key: (revision or {}).get(key) for key in ("reviewerId", "reviewerRole", "createdAt", "validatedAt", "approvedAt")},
            "machineScore": executive.get("overallScore"), "collectionCoverage": summary.get("coverageRatio"),
            "measurementCoverage": executive.get("overallCoverage"), "priorities": active_priorities, "completeFindings": complete,
            "methodology": ["Representative sampling and Phase 2A collection coverage.", "Deterministic evidence-aware checks and safe interaction testing."],
            "limitations": ["Automated accessibility does not establish complete WCAG conformance.", "Lighthouse is laboratory data, not CrUX or field data.", "VLM interpretation is probabilistic; complex contrast and logical focus order may require human review."],
            "tools": machine.get("toolMetadata") or {},
            "siteUrl": str((machine.get("site") if isinstance(machine.get("site"), dict) else {}).get("homepage") or (machine.get("site") if isinstance(machine.get("site"), dict) else {}).get("url") or ""),
            "language": str(machine.get("language") or "en")}


def render_reviewed_report(context: dict[str, Any]) -> str:
    """Reviewed snapshots use the EY Studio+ client report renderer."""
    from src.report.client.context import client_context_from_reviewed
    from src.report.client.render import render_client_report

    return render_client_report(client_context_from_reviewed(context))
