"""Small immutable review-report context and safe HTML renderer for Phase 4A."""
from __future__ import annotations

import html
from typing import Any


def reviewed_report_context(*, audit_id: str, machine: dict[str, Any], revision: dict[str, Any] | None) -> dict[str, Any]:
    changes = (revision or {}).get("changes") if isinstance((revision or {}).get("changes"), dict) else {}
    findings = machine.get("allFindings") or machine.get("findings") or []
    priorities = machine.get("priorities") or machine.get("executiveSummary", {}).get("topPriorities") or []
    complete = []
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, dict): continue
        item = dict(finding); item["review"] = changes.get(str(finding.get("findingId") or finding.get("id") or ""), {})
        complete.append(item)
    active_priorities = [item for item in priorities if not (changes.get(str(item.get("findingId") or item.get("id") or ""), {}) or {}).get("suppressed")]
    summary = machine.get("summary") if isinstance(machine.get("summary"), dict) else {}
    executive = machine.get("executiveSummary") if isinstance(machine.get("executiveSummary"), dict) else {}
    return {"auditId": audit_id, "revisionId": (revision or {}).get("revisionId"), "reviewStatus": (revision or {}).get("reviewStatus", "unreviewed"),
            "reviewer": {key: (revision or {}).get(key) for key in ("reviewerId", "reviewerRole", "createdAt", "validatedAt", "approvedAt")},
            "machineScore": executive.get("overallScore"), "collectionCoverage": summary.get("coverageRatio"),
            "measurementCoverage": executive.get("overallCoverage"), "priorities": active_priorities, "completeFindings": complete,
            "methodology": ["Representative sampling and Phase 2A collection coverage.", "Deterministic evidence-aware checks and safe interaction testing."],
            "limitations": ["Automated accessibility does not establish complete WCAG conformance.", "Lighthouse is laboratory data, not CrUX or field data.", "VLM interpretation is probabilistic; complex contrast and logical focus order may require human review."],
            "tools": machine.get("toolMetadata") or {}}


def render_reviewed_report(context: dict[str, Any]) -> str:
    def esc(value: Any) -> str: return html.escape(str(value or ""), quote=True)
    status = context["reviewStatus"]
    label = "Machine audit — not reviewed" if status == "unreviewed" else status.replace("_", " ").title()
    findings = "".join(
        f"<article><h3>{esc(item.get('title') or item.get('findingId'))}</h3><p>Machine assessment: {esc(item.get('outcome') or item.get('status'))}</p><p>Rule: {esc(item.get('ruleId'))}; Evidence: {esc(', '.join(item.get('evidenceIds') or []))}</p>"
        f"<p>Reviewer decision: {esc((item.get('review') or {}).get('reviewDecision'))}</p><p>Reviewer note: {esc((item.get('review') or {}).get('reviewNote'))}</p>"
        f"<p>{'Suppressed from executive priorities: ' + esc((item.get('review') or {}).get('suppressionReason')) if (item.get('review') or {}).get('suppressed') else ''}</p></article>"
        for item in context["completeFindings"])
    return f"<!doctype html><html><body><header><h1>Audit report</h1><p>Review status: {esc(label)}</p><p>Revision: {esc(context.get('revisionId'))}; Reviewer: {esc(context['reviewer'].get('reviewerId'))}</p></header><section><h2>Executive summary</h2><p>Priority findings: {len(context['priorities'])}</p></section><section><h2>Scope and coverage</h2><p>Collection coverage: {esc(context.get('collectionCoverage'))}; Measurement coverage: {esc(context.get('measurementCoverage'))}</p></section><section><h2>Complete findings</h2>{findings}</section><section><h2>Methodology</h2>{''.join('<p>'+esc(x)+'</p>' for x in context['methodology'])}</section><section><h2>Limitations</h2>{''.join('<p>'+esc(x)+'</p>' for x in context['limitations'])}</section><section><h2>Tool and provenance metadata</h2><pre>{esc(context['tools'])}</pre></section></body></html>"
