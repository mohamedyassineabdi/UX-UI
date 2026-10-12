"""Methodology v3 evidence eligibility: which findings may affect a score."""
from __future__ import annotations

import math

from .config import Criterion


def normalize_confidence(value: object) -> float:
    """Return confidence in 0..1.

    Numbers and numeric strings are accepted. Only values above 1 are read as
    percentages (85 -> 0.85, 1.4 -> 0.014); 1 itself means certainty. Anything
    unparsable, including booleans, becomes 0.
    """
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(number):
        return 0.0
    if number > 1:
        number /= 100
    return min(max(number, 0.0), 1.0)


def _has_location(row: dict) -> bool:
    return bool(row.get("elementIds")) or bool(row.get("screenshotRegion"))


def is_score_eligible(row: dict, criterion: Criterion, gate: float) -> bool:
    """Measured evidence always counts; AI evidence needs confidence and a location; manual needs confirmation.

    AI passes are reported as criterion ids with nothing to point at, so only
    non-pass AI rows must cite element ids or a screenshot region.
    """
    if criterion.evidence_type == "measured":
        return True
    if criterion.evidence_type == "ai_assessed":
        confident = normalize_confidence(row.get("confidence")) >= gate
        return confident and (row.get("outcome") == "pass" or _has_location(row))
    return row.get("reviewStatus") == "confirmed"
