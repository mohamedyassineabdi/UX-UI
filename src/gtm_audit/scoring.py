"""Phase 3A internal audit scoring methodology.

Scores are compliance results from applicable, measured pass/fail rules only.
Warnings are cautions (not half-credit); missing evidence affects coverage and
confidence, never the numerical compliance result.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Iterable


AXIS_IDS = ("task_execution", "flow_architecture", "trust_accessibility", "ui_consistency", "content_microcopy")

# Deliberate methodology registry.  Keys are stable sheet/row rule keys emitted
# by the workbook check catalogue, not prose keyword matches.
SHEET_AXIS_MAP = {
    "Content": {"content_microcopy": 1.0, "trust_accessibility": 0.5},
    "Labeling": {"content_microcopy": 1.0, "task_execution": 0.5},
    "Navigation": {"flow_architecture": 1.0},
    "Feedback": {"task_execution": 1.0},
    "Forms": {"task_execution": 1.0, "trust_accessibility": 0.5},
    "Interaction": {"task_execution": 1.0},
    "Presentation": {"ui_consistency": 1.0},
    "Visual hierarchy": {"ui_consistency": 1.0, "content_microcopy": 0.5},
}
RULE_AXIS_MAP: dict[str, dict[str, float]] = {}


@dataclass(frozen=True)
class ScoreResult:
    score: float | None
    scored: bool
    reason: str | None
    measured_weight: float
    applicable_weight: float
    confidence: float | None
    coverage: float
    measured_count: int
    applicable_count: int
    unknown_count: int
    not_measured_count: int
    collection_failed_count: int
    warning_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rule_key(row: dict[str, Any]) -> str:
    return str(row.get("ruleKey") or row.get("machine_criterion") or f"{row.get('sheet', '')}:{row.get('row', '')}").strip()


def axis_mapping(row: dict[str, Any]) -> dict[str, float]:
    """Return intentional mapping only; unknown rules are not scored."""
    explicit = RULE_AXIS_MAP.get(str(row.get("ruleId") or "")) or RULE_AXIS_MAP.get(rule_key(row))
    if explicit:
        return dict(explicit)
    # Phase 2B hashed IDs identify catalogued workbook rows. Arbitrary custom
    # IDs require an explicit registry entry and are surfaced as unmapped.
    if str(row.get("ruleId") or "").startswith("rule_"):
        return dict(SHEET_AXIS_MAP.get(str(row.get("sheet") or ""), {}))
    return {}


def _state(row: dict[str, Any]) -> tuple[str, str, str]:
    outcome = str(row.get("outcome") or row.get("status") or "unknown").lower()
    outcome = {"true": "pass", "false": "fail", "n/a": "unknown", "na": "unknown"}.get(outcome, outcome)
    applicability = str(row.get("applicability") or "applicable").lower()
    measurement = str(row.get("measurement") or ("measured" if outcome in {"pass", "fail", "warning"} else "not_measured")).lower()
    return outcome, applicability, measurement


def score_axis(rows: Iterable[dict[str, Any]]) -> ScoreResult:
    ordered = sorted((dict(row) for row in rows), key=lambda row: (str(row.get("ruleId") or rule_key(row)), str(row.get("findingId") or "")))
    applicable_weight = measured_weight = points = confidence_weight = 0.0
    applicable_count = measured_count = unknown = not_measured = collection_failed = warnings = 0
    for row in ordered:
        outcome, applicability, measurement = _state(row)
        weight = float(row.get("axisWeight", 1.0) or 1.0)
        if applicability != "applicable":
            continue
        applicable_count += 1
        applicable_weight += weight
        if measurement == "collection_failed":
            collection_failed += 1
            continue
        if measurement != "measured":
            not_measured += 1
            if outcome == "unknown":
                unknown += 1
            continue
        if outcome == "warning":
            warnings += 1
            continue
        if outcome not in {"pass", "fail"}:
            unknown += 1
            continue
        measured_count += 1
        measured_weight += weight
        points += weight if outcome == "pass" else 0.0
        confidence_weight += weight * max(0.0, min(1.0, float(row.get("confidence", 0.5) or 0.5)))
    coverage = measured_weight / applicable_weight if applicable_weight else 0.0
    confidence = confidence_weight / measured_weight if measured_weight else None
    if not measured_weight:
        return ScoreResult(None, False, "No applicable measured pass/fail evidence.", measured_weight, applicable_weight, confidence, coverage, measured_count, applicable_count, unknown, not_measured, collection_failed, warnings)
    return ScoreResult(points / measured_weight * 100.0, True, None, measured_weight, applicable_weight, confidence, coverage, measured_count, applicable_count, unknown, not_measured, collection_failed, warnings)


def _fingerprint(finding: dict[str, Any]) -> str:
    target = finding.get("target") or finding.get("element") or finding.get("evidenceFingerprint") or ""
    provenance = finding.get("provenance") or {}
    pages = provenance.get("pageRefs", []) if isinstance(provenance, dict) else []
    page_ids = ",".join(sorted(str(p.get("pageId") or "") for p in pages if isinstance(p, dict)))
    rule = finding.get("ruleId") or finding.get("ruleKey") or finding.get("criterion") or ""
    raw = "|".join(str(value).strip().lower() for value in (rule, page_ids, target))
    return sha256(raw.encode()).hexdigest()[:20]


def deduplicate_findings(findings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        groups[_fingerprint(finding)].append(dict(finding))
    merged = []
    for fingerprint in sorted(groups):
        items = sorted(groups[fingerprint], key=lambda item: (str(item.get("findingId") or ""), str(item.get("source") or "")))
        primary = dict(items[0])
        primary["deduplicationId"] = f"defect_{fingerprint}"
        primary["sources"] = sorted({str(i.get("source") or i.get("source_type") or "deterministic") for i in items})
        primary["evidenceIds"] = sorted({str(e) for i in items for e in (i.get("evidenceIds") or []) if e})
        primary["confirmationCount"] = len(items)
        merged.append(primary)
    return merged


def critical_eligible(finding: dict[str, Any]) -> bool:
    outcome, applicability, measurement = _state(finding)
    provenance = finding.get("provenance") or {}
    return outcome == "fail" and applicability == "applicable" and measurement == "measured" and str(finding.get("severity") or "").lower() == "critical" and provenance.get("status") != "unresolved"


def overall_score(axis_results: Iterable[ScoreResult], findings: Iterable[dict[str, Any]]) -> dict[str, Any]:
    results = list(axis_results)
    scored = [result for result in results if result.scored and result.score is not None]
    score = sum(result.score for result in scored) / len(scored) if scored else None
    coverage = sum(result.coverage for result in results) / len(results) if results else 0.0
    critical = any(critical_eligible(finding) for finding in findings)
    return {"score": score, "scored": bool(scored), "reason": None if scored else "No audit axes have applicable measured evidence.", "axesScored": len(scored), "axesTotal": len(results), "coverage": coverage, "criticalFindingCount": sum(1 for finding in findings if critical_eligible(finding)), "hasCriticalBlocker": critical, "rating": "Blocked" if critical else ("Not scored" if score is None else "Measured")}
