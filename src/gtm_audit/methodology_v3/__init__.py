"""UX/UI audit methodology v3: config, severity, eligibility, scoring."""
from .config import (
    AXIS_IDS,
    Axis,
    Criterion,
    LocalizedText,
    MaturityBand,
    Methodology,
    OutOfScope,
    ScoringConfig,
    load_methodology,
)
from .eligibility import is_score_eligible, normalize_confidence
from .scoring import AxisScore, Coverage, OverallScore, dedupe_key, maturity_for, overall_v3, score_axis_v3, unscored_rows
from .severity import Severity, escalate

__all__ = [
    "AXIS_IDS",
    "Axis",
    "AxisScore",
    "Coverage",
    "Criterion",
    "LocalizedText",
    "MaturityBand",
    "Methodology",
    "OutOfScope",
    "OverallScore",
    "ScoringConfig",
    "Severity",
    "dedupe_key",
    "escalate",
    "is_score_eligible",
    "load_methodology",
    "maturity_for",
    "normalize_confidence",
    "overall_v3",
    "score_axis_v3",
    "unscored_rows",
]
