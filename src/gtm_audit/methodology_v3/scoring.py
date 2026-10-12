"""Methodology v3 axis scoring: dedupe, penalties, maturity caps, coverage."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Sequence

from .config import Axis, Criterion, LocalizedText, MaturityBand, Methodology, ScoringConfig
from .eligibility import is_score_eligible
from .severity import Severity, escalate

# Worst first: a key keeps its worst outcome.
_OUTCOME_RANK = {"fail": 0, "warning": 1, "unknown": 2, "pass": 3}


@dataclass(frozen=True)
class Coverage:
    evaluated: int
    applicable: int
    not_applicable_for_target: tuple[str, ...]
    not_evaluated: tuple[str, ...]


@dataclass(frozen=True)
class AxisScore:
    axis_id: str
    score: float
    maturity: int
    maturity_label: LocalizedText
    coverage: Coverage
    worst_severity: Severity | None
    scored_defects: int
    observations: tuple[dict, ...]
    escalations: tuple[str, ...]


def dedupe_key(row: dict, criterion: Criterion, index: int | None = None) -> str:
    """One logical defect = family + page + elements (spec §6.2).

    Region-only AI findings add their screenshot region. Rows with no page,
    elements, or region fall back to their findingId, then to their position
    in the input (`index`), so distinct defects never collapse into one.
    """
    page = str(row.get("pageId") or "")
    elements = ",".join(sorted(str(item) for item in row.get("elementIds") or ()))
    location = elements
    if not elements and isinstance(row.get("screenshotRegion"), dict) and row["screenshotRegion"]:
        location = "region:" + json.dumps(row["screenshotRegion"], sort_keys=True)
    if not page and not location:
        finding = row.get("findingId") or (f"#{index}" if index is not None else f"@{id(row)}")
        return f"{criterion.logical_defect_family}|finding:{finding}"
    return f"{criterion.logical_defect_family}|{page}|{location}"


def _severity(value: object) -> Severity:
    if isinstance(value, Severity):
        return value
    try:
        return Severity(str(value).strip().lower())
    except ValueError:
        return Severity.MEDIUM


def _outcome(row: dict) -> str:
    value = str(row.get("outcome") or "unknown").lower()
    return value if value in _OUTCOME_RANK else "unknown"


def maturity_for(score: float, worst: Severity | None, bands: Sequence[MaturityBand]) -> int:
    level = next((band.level for band in bands if score >= band.min_score), bands[-1].level)
    if worst is Severity.CRITICAL:
        level = min(level, 2)
    elif worst is Severity.HIGH:
        level = min(level, 4)
    return level


def _label(level: int, bands: Sequence[MaturityBand]) -> LocalizedText:
    return next(band.label for band in bands if band.level == level)


def _applies(criterion: Criterion, target: str, page_types: frozenset[str] | None) -> bool:
    if target not in criterion.targets:
        return False
    return page_types is None or "any" in criterion.page_types or bool(page_types.intersection(criterion.page_types))


def score_axis_v3(
    rows: Iterable[dict],
    axis: Axis,
    target: str,
    scoring: ScoringConfig,
    page_types: Iterable[str] | None = None,
) -> AxisScore | None:
    """Score one axis. `page_types` (the page types audited) narrows applicability; None means all."""
    audited = frozenset(page_types) if page_types is not None else None
    applicable = {c.id: c for c in axis.criteria if _applies(c, target, audited)}
    if not applicable:
        return None
    not_applicable = tuple(c.id for c in axis.criteria if c.id not in applicable)

    observations: list[dict] = []
    criterion_outcomes: dict[str, str] = {}
    defects: dict[str, tuple[Severity, str | None]] = {}  # key -> (severity after escalation, escalated finding)
    for index, row in enumerate(rows):
        criterion = applicable.get(str(row.get("criterionId") or ""))
        if criterion is None:
            continue  # unknown, other axis, or not applicable to this target
        outcome = _outcome(row)
        if not is_score_eligible(row, criterion, scoring.ai_confidence_gate):
            if outcome != "pass":
                observations.append(row)
            continue
        current = criterion_outcomes.get(criterion.id)
        if current is None or _OUTCOME_RANK[outcome] < _OUTCOME_RANK[current]:
            criterion_outcomes[criterion.id] = outcome
        if outcome != "fail":
            continue
        severity, escalated = escalate(_severity(row.get("severity")), bool(row.get("onKeyTask")))
        key = dedupe_key(row, criterion, index)
        kept = defects.get(key)
        if kept is None or severity.rank < kept[0].rank:
            defects[key] = (severity, str(row.get("findingId") or criterion.id) if escalated else None)

    evaluated = [cid for cid, outcome in criterion_outcomes.items() if outcome in ("pass", "fail")]
    total_weight = sum(applicable[cid].numeric_weight for cid in evaluated)
    passed_weight = sum(applicable[cid].numeric_weight for cid in evaluated if criterion_outcomes[cid] == "pass")
    base = 100.0 * passed_weight / total_weight if total_weight else 0.0
    penalty = sum(scoring.penalties[severity.value] for severity, _ in defects.values())
    score = min(max(base - penalty, 0.0), 100.0)

    worst = min((severity for severity, _ in defects.values()), key=lambda s: s.rank, default=None)
    bands = scoring.maturity_bands
    maturity = maturity_for(score, worst, bands)
    return AxisScore(
        axis_id=axis.id,
        score=score,
        maturity=maturity,
        maturity_label=_label(maturity, bands),
        coverage=Coverage(
            evaluated=len(evaluated),
            applicable=len(applicable),
            not_applicable_for_target=not_applicable,
            not_evaluated=tuple(cid for cid in applicable if cid not in evaluated),
        ),
        worst_severity=worst,
        scored_defects=len(defects),
        observations=tuple(observations),
        escalations=tuple(finding for _, finding in defects.values() if finding),
    )


@dataclass(frozen=True)
class OverallScore:
    score: float
    maturity: int
    maturity_label: LocalizedText
    weights_used: dict[str, float]
    axes_scored: int


def overall_v3(axis_scores: Iterable[AxisScore | None], product_type: str | None, methodology: Methodology) -> OverallScore:
    """Weighted mean of scored axes; maturity capped at (worst axis level + 1).

    Axes that are None or evaluated nothing are left out, so missing evidence
    never drags the headline down as if it were a failure.
    """
    scored = [axis for axis in axis_scores if axis is not None and axis.coverage.evaluated > 0]
    table = methodology.product_type_weights.get(product_type or "", {})
    weights = {axis.axis_id: float(table.get(axis.axis_id, 1.0)) for axis in scored}
    bands = methodology.scoring.maturity_bands
    if not scored:
        level = bands[-1].level
        return OverallScore(0.0, level, _label(level, bands), {}, 0)
    score = sum(axis.score * weights[axis.axis_id] for axis in scored) / sum(weights.values())
    level = min(maturity_for(score, None, bands), min(axis.maturity for axis in scored) + 1)
    return OverallScore(score, level, _label(level, bands), weights, len(scored))


def unscored_rows(rows, methodology):
    return ()


def unscored_rows(rows: Iterable[dict], methodology: Methodology) -> tuple[dict, ...]:
    """Rows naming a criterion the methodology does not know (typo, or a check not yet configured).

    score_axis_v3 skips them; the report lists them as unscored. Rows with no
    criterionId at all are not findings and are left out.
    """
    return tuple(row for row in rows if row.get("criterionId") and methodology.criterion(str(row["criterionId"])) is None)
