"""Presentation-ready, JSON-serialisable facts for the client report. Pure: no I/O, never mutates input."""
from __future__ import annotations

import datetime as _dt
import math
import re
from urllib.parse import urlparse
from typing import Any

from src.report.reviewed_report import reviewed_report_context
from src.report.roadmap_teaser import NON_FAILING

SEVERITIES = ("critical", "high", "medium", "low")
LIMITATIONS = [
    "Automated accessibility checks do not establish complete WCAG conformance.",
    "Performance figures are laboratory measurements, not field data from real visitors.",
    "AI interpretation of screenshots is probabilistic; contrast and focus order may need human confirmation.",
]
# Plain-language answer to "how do we know?", in the order the appendix lists them.
METHODS = ("Automated accessibility test (WCAG)", "Automated checklist test on the page code", "Lab performance test",
           "AI agent review of screenshots", "Expert visual review")
METHODOLOGY = [
    "Scope: we visited the homepage and the key pages a visitor relies on, and captured each one as it renders in a real browser.",
    "Measure: every page was checked with automated accessibility tests (WCAG), a UX checklist measured on the page code, "
    "and the AI agent's review of the screenshots.",
    "Prioritise: findings were ranked by severity and business impact; only the most important ones drive the recommendations.",
]
REVIEWED = {"validated", "approved"}
ROADMAP_LANE_LIMIT = 5


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(_text(item) for item in value if item)
    return "" if value is None else str(value).strip()


def _number(value: Any) -> float | None:
    try:
        number = None if value is None or isinstance(value, bool) else float(value)
    except (TypeError, ValueError):
        return None
    return number if number is not None and math.isfinite(number) else None


def _severity(value: Any) -> str:
    value = _text(value).lower()
    return value if value in SEVERITIES else "low"


def _band(score: float | None, scored: bool) -> str:
    if score is None or not scored:
        return "none"
    return "green" if score >= 70 else "amber" if score >= 50 else "red"


def _title(item: Any) -> str:
    return _text(item.get("title") if isinstance(item, dict) else item)


def _name(value: Any) -> str:
    return _text(value.get("name") or value.get("shortName")) if isinstance(value, dict) else _text(value)


def _identity(item: dict[str, Any]) -> str:
    return _text(item.get("findingId") or item.get("id") or item.get("deduplicationId"))


def _method(item: dict[str, Any], source: str, ai: bool) -> str:
    signals = " ".join((source, _text(item.get("measurementClass")), _text(item.get("ruleId")), _text(item.get("sources")), _text(item.get("sourceSheet")))).lower()
    if ai or "ai_visual" in signals or "vision" in signals or "ai discovery" in signals:
        return METHODS[3]
    if "axe" in signals or "standards_automated" in signals:
        return METHODS[0]
    if "lighthouse" in signals or "performance" in signals:
        return METHODS[2]
    return METHODS[4] if "manual" in signals else METHODS[1]


def _page(item: dict[str, Any]) -> str:
    url, name = _text(item.get("pageUrl")), _text(item.get("pageName"))
    if url:
        return urlparse(url).path or "/"
    return "Site-wide" if name.lower() in {"", "the audited journey"} else name  # generate_gtm_audit's placeholder for cross-page findings


def _finding_record(item: dict[str, Any], key: str, ai: bool) -> dict[str, Any]:
    review = _dict(item.get("review"))
    override = _text(review.get("priorityOverride")).lower()
    bundle = _dict(item.get("evidenceBundle"))
    target = bundle.get("target")
    source = _text(bundle.get("source") or item.get("measurementMethod") or ("AI agent" if ai else ""))
    criterion = _text(item.get("wcagCriterion") or bundle.get("criterion"))
    return {
        "key": key, "title": _text(item.get("title")) or "Untitled finding",
        "severity": override if override in SEVERITIES else _severity(item.get("severity")),
        "axis": _text(item.get("axisName") or item.get("sourceSheet")), "pageName": _text(item.get("pageName")), "pageUrl": _text(item.get("pageUrl")),
        "problem": _text(item.get("explanation")) or _text(item.get("evidence")), "whyItMatters": _text(item.get("whyItMatters")),
        "recommendation": _text(review.get("reviewedRecommendation")) or _text(item.get("recommendation")),
        "reviewerNote": _text(review.get("reviewNote")), "reviewerPriority": override if override in SEVERITIES else "",
        "aiDiscovered": ai, "screenshotPath": _text(item.get("screenshotPath")),
        "visualRegion": item.get("visualRegion") if isinstance(item.get("visualRegion"), dict) else None,
        "evidenceBundle": bundle or None,
        "provenance": {"source": source, "criterion": criterion, "method": _method(item, source, ai),
                       "standard": f"WCAG {criterion}" if re.fullmatch(r"\d+\.\d+(\.\d+)?", criterion) else "",
                       "page": _page(item),
                       "selector": _text(target.get("selector") if isinstance(target, dict) else target),
                       "measurementClass": _text(item.get("measurementClass")), "evidence": _text(item.get("evidence"))},
    }


def _findings(reviewed: dict[str, Any], machine: dict[str, Any], changes: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    findings, excluded, defects = [], [], set()
    for index, item in enumerate(reviewed["completeFindings"]):
        defect = _text(item.get("deduplicationId"))
        if _text(item.get("outcome") or item.get("status")).lower() in NON_FAILING or (defect and defect in defects):
            continue
        defects.add(defect)
        review = _dict(item.get("review"))
        if review.get("suppressed"):
            excluded.append({"title": _text(item.get("title")) or "Untitled finding", "reason": _text(review.get("suppressionReason"))})
        else:
            findings.append(_finding_record(item, _identity(item) or f"f-{index}", bool(item.get("aiDiscovered"))))
    # AI findings live in their own list; the review workspace edits them by the same "ai-<n>" key.
    seen = {(f["title"], f["pageUrl"]) for f in findings}
    suppressed_titles = {e["title"] for e in excluded}
    for index, item in enumerate(_list(machine.get("aiDiscoveredFindings"))):
        title = _text(item.get("title")) if isinstance(item, dict) else ""
        if not isinstance(item, dict) or (title, _text(item.get("pageUrl"))) in seen or title in suppressed_titles:
            continue
        key = _identity(item) or f"ai-{index}"
        review = _dict(changes.get(key))
        if review.get("suppressed"):
            excluded.append({"title": title or "Untitled finding", "reason": _text(review.get("suppressionReason"))})
            continue
        findings.append(_finding_record({**item, "review": review}, key, True))
    findings.sort(key=lambda f: SEVERITIES.index(f["severity"]))
    return findings, excluded


def _sanitised(machine: Any) -> dict[str, Any]:
    """Drop malformed sections so one bad field never breaks the deliverable."""
    machine = dict(_dict(machine))
    for key in ("executiveSummary", "summary", "site", "coverage"):
        if key in machine:
            machine[key] = _dict(machine[key])
    for key in ("priorities", "allFindings", "findings", "deduplicatedFindings", "aiDiscoveredFindings", "axes", "recommendations", "scannedPages"):
        if key in machine:
            machine[key] = [item for item in _list(machine[key]) if isinstance(item, dict)]
    if isinstance(machine.get("executiveSummary"), dict) and "topPriorities" in machine["executiveSummary"]:
        machine["executiveSummary"] = {**machine["executiveSummary"], "topPriorities": [item for item in _list(machine["executiveSummary"]["topPriorities"]) if isinstance(item, dict)]}
    return machine


def _capped(items: list[str], limit: int = 4) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out[:limit]


def _review(revision: dict[str, Any] | None, reviewed: dict[str, Any]) -> dict[str, Any]:
    status = _text((revision or {}).get("reviewStatus")) or "unreviewed"
    label = ("Automated audit — not reviewed" if status == "unreviewed"
             else "Reviewed and validated by EY Studio+" if status in REVIEWED else "Expert review in progress")
    return {"status": status, "label": label, "revisionId": reviewed.get("revisionId"), "reviewer": reviewed.get("reviewer") or {}}


def build_client_report_context(*, audit_id: str, machine: dict[str, Any], revision: dict[str, Any] | None, audit_date: str | None = None) -> dict[str, Any]:
    machine = _sanitised(machine)
    reviewed = reviewed_report_context(audit_id=audit_id, machine=machine, revision=revision)
    changes = _dict((revision or {}).get("changes"))
    site = _dict(machine.get("site"))
    executive = _dict(machine.get("executiveSummary"))
    findings, excluded = _findings(reviewed, machine, changes)
    hidden = {e["title"] for e in excluded}
    counts = {severity: sum(1 for f in findings if f["severity"] == severity) for severity in SEVERITIES}
    axes = [{"id": _text(axis.get("id")), "name": _name(axis), "score": _number(axis.get("score")), "scored": axis.get("scored") is not False and _number(axis.get("score")) is not None,
             "summary": _text(axis.get("summary")), "_source": axis} for axis in _list(machine.get("axes")) if isinstance(axis, dict)]
    for axis in axes:
        axis["band"] = _band(axis["score"], axis["scored"])
    by_strength = sorted(axes, key=lambda a: -(a["score"] if a["scored"] else -1))
    by_weakness = sorted(axes, key=lambda a: a["score"] if a["scored"] else 101)
    recommendations = [r for r in _list(machine.get("recommendations")) if isinstance(r, dict)]
    roadmap: dict[str, list[dict[str, str]]] = {"now": [], "next": [], "later": []}
    for finding in findings:  # already ordered by severity
        bucket = "now" if finding["severity"] in {"critical", "high"} else "next" if finding["severity"] == "medium" else "later"
        if len(roadmap[bucket]) < ROADMAP_LANE_LIMIT:
            roadmap[bucket].append({"title": finding["title"], "description": finding["recommendation"], "axis": finding["axis"]})
    pages = [{"name": _text(p.get("page_name") or p.get("title")), "url": _text(p.get("page_url")), "path": urlparse(_text(p.get("page_url"))).path or "/"}
             for p in _list(machine.get("scannedPages")) if isinstance(p, dict)]
    methods = [{"label": m, "count": n} for m in METHODS if (n := sum(1 for f in findings if f["provenance"]["method"] == m))]
    context = {
        "auditId": audit_id, "site": {"name": _text(site.get("domain")) or urlparse(_text(site.get("homepage") or site.get("url"))).netloc or "Audited site", "url": _text(site.get("homepage") or site.get("url"))},
        "language": _text(site.get("language") or machine.get("language")) or "en",
        "auditDate": audit_date or _dt.date.today().isoformat(), "review": _review(revision, reviewed),
        "overall": {"score": _number(executive.get("overallScore")), "rating": _text(executive.get("overallRating")), "reason": _text(executive.get("overallReason"))},
        "kpis": {"pagesAudited": len(pages), "findings": len(findings), "critical": counts["critical"],
                 "blockers": bool(executive.get("hasCriticalBlocker")) or counts["critical"] > 0},
        "positioningHook": _text(executive.get("positioningHook")),
        # Taken from the reviewed findings so overrides, edits and exclusions always apply.
        "topPriorities": [{"title": f["title"], "axis": f["axis"], "severity": f["severity"], "recommendation": f["recommendation"]} for f in findings[:3]],
        "axes": [{k: v for k, v in axis.items() if k != "_source"} for axis in axes],
        "severityCounts": counts,
        "strongestAxis": _name(executive.get("strongestAxis")), "weakestAxis": _name(executive.get("weakestAxis")),
        "insights": {"strengths": _capped([_title(s) for a in by_strength for s in _list(a["_source"].get("strengths"))]),
                     "improvements": _capped([_title(s) for a in by_weakness for s in _list(a["_source"].get("painPoints")) if _title(s) not in hidden]),
                     "opportunities": _capped([_title(s) for a in by_weakness for s in _list(a["_source"].get("opportunities"))]),
                     "recommendations": _capped([_title(r) for r in recommendations if _title(r) not in hidden])},
        "findings": findings, "excluded": excluded, "roadmap": roadmap,
        "appendix": {"methodology": METHODOLOGY, "methods": methods, "coverage": pages, "limitations": LIMITATIONS},
    }
    return context


def client_context_from_reviewed(reviewed: dict[str, Any]) -> dict[str, Any]:
    """Adapt a legacy reviewed-report context (review edits already merged) into a client context."""
    changes, findings = {}, []
    for item in _list(reviewed.get("completeFindings")):
        if not isinstance(item, dict):
            continue
        findings.append({k: v for k, v in item.items() if k != "review"})
        if _identity(item):
            changes[_identity(item)] = _dict(item.get("review"))
    machine = {"deduplicatedFindings": findings, "priorities": _list(reviewed.get("priorities")),
               "site": {"homepage": reviewed.get("siteUrl") or ""}, "language": reviewed.get("language") or "en"}
    revision = {"revisionId": reviewed.get("revisionId"), "reviewStatus": reviewed.get("reviewStatus") or "unreviewed", "changes": changes,
                **_dict(reviewed.get("reviewer"))}
    return build_client_report_context(audit_id=_text(reviewed.get("auditId")), machine=machine, revision=revision)
