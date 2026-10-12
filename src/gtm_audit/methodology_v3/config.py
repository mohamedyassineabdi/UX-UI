"""Methodology v3 config: frozen pydantic models and a validated loader."""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = ROOT_DIR / "shared" / "config" / "audit_methodology_v3.json"
AXIS_IDS = ("usability", "navigation", "visual", "content", "accessibility", "performance", "trust")
SEVERITY_KEYS = frozenset({"critical", "high", "medium", "low"})
WEIGHTS = {"core": 3, "supporting": 1}
PAGE_TYPES = frozenset({"any", "form", "checkout", "listing", "article", "dashboard"})
STANDARD_PATTERN = re.compile(
    r"^(WCAG22:\d\.\d+\.\d+|NNG:H(10|[1-9])|CWV:(LCP|INP|CLS|FCP|TTFB)|GESTALT:\w+"
    r"|BAYMARD:[\w-]+|ISO9241:[\w.-]+|NNG:[\w-]+|STANFORD:[\w-]+)$"
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LocalizedText(_Frozen):
    en: str
    fr: str

    @field_validator("en", "fr")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("localized text must be non-empty in every language")
        return value


class Criterion(_Frozen):
    id: str
    title: LocalizedText
    description: LocalizedText
    weight: Literal["core", "supporting"]
    standards: tuple[str, ...] = Field(min_length=1)
    targets: tuple[Literal["website", "webapp", "figma", "mobile"], ...] = Field(min_length=1)
    page_types: tuple[str, ...] = Field(min_length=1)
    evidence_type: Literal["measured", "ai_assessed", "manual_only"]
    pass_guidance: LocalizedText
    fail_guidance: LocalizedText
    example_good: LocalizedText
    example_rejected: LocalizedText
    logical_defect_family: str = Field(min_length=1)

    @field_validator("standards")
    @classmethod
    def _known_standards(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [item for item in value if not STANDARD_PATTERN.match(item)]
        if unknown:
            raise ValueError(f"unknown standard reference(s): {unknown}")
        return value

    @field_validator("page_types")
    @classmethod
    def _known_page_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = sorted(set(value) - PAGE_TYPES)
        if unknown:
            raise ValueError(f"unknown page type(s): {unknown}; expected {sorted(PAGE_TYPES)}")
        return value

    @property
    def numeric_weight(self) -> int:
        return WEIGHTS[self.weight]


class OutOfScope(_Frozen):
    topic: str = Field(min_length=1)
    routes_to: str


class Axis(_Frozen):
    id: str
    name: LocalizedText
    core_question: LocalizedText
    why_it_matters: LocalizedText
    failure_modes: tuple[LocalizedText, ...]
    out_of_scope: tuple[OutOfScope, ...]
    criteria: tuple[Criterion, ...]

    @model_validator(mode="after")
    def _criteria_belong_to_axis(self) -> "Axis":
        for criterion in self.criteria:
            if not criterion.id.startswith(f"{self.id}."):
                raise ValueError(f"criterion {criterion.id!r} must be prefixed {self.id!r}.")
        for item in self.out_of_scope:
            if item.routes_to == self.id or item.routes_to not in AXIS_IDS:
                raise ValueError(f"out_of_scope on {self.id!r} must route to another axis, got {item.routes_to!r}")
        return self


class MaturityBand(_Frozen):
    level: int
    label: LocalizedText
    min_score: int


class ScoringConfig(_Frozen):
    penalties: dict[str, int]
    ai_confidence_gate: float = Field(ge=0, le=1)
    maturity_bands: tuple[MaturityBand, ...]

    @model_validator(mode="after")
    def _check(self) -> "ScoringConfig":
        if set(self.penalties) != SEVERITY_KEYS:
            raise ValueError(f"penalties must have exactly {sorted(SEVERITY_KEYS)}")
        if [band.level for band in self.maturity_bands] != [5, 4, 3, 2, 1]:
            raise ValueError("maturity bands must be levels 5..1 in order")
        scores = [band.min_score for band in self.maturity_bands]
        if any(high <= low for high, low in zip(scores, scores[1:])):
            raise ValueError("maturity band min_score must strictly descend")
        return self


class Methodology(_Frozen):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    version: Literal[3]
    axes: tuple[Axis, ...]
    scoring: ScoringConfig
    product_type_weights: dict[str, dict[str, float]] = Field(default_factory=dict, alias="productTypeWeights")

    @model_validator(mode="after")
    def _check(self) -> "Methodology":
        if tuple(axis.id for axis in self.axes) != AXIS_IDS:
            raise ValueError(f"axes must be exactly {list(AXIS_IDS)} in order")
        ids = [criterion.id for axis in self.axes for criterion in axis.criteria]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            raise ValueError(f"duplicate criterion ids: {duplicates}")
        for product_type, weights in self.product_type_weights.items():
            for axis_id, weight in weights.items():
                if axis_id not in AXIS_IDS or weight <= 0:
                    raise ValueError(f"productTypeWeights[{product_type!r}] has invalid entry {axis_id!r}: {weight!r}")
        return self

    def axis(self, axis_id: str) -> Axis:
        for axis in self.axes:
            if axis.id == axis_id:
                return axis
        raise KeyError(axis_id)

    def criterion(self, criterion_id: str) -> Criterion | None:
        return self._criteria_by_id().get(criterion_id)

    def _criteria_by_id(self) -> dict[str, Criterion]:
        return {criterion.id: criterion for axis in self.axes for criterion in axis.criteria}


def _read(path: Path) -> Methodology:
    return Methodology.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


@lru_cache(maxsize=4)
def _load_default(path: str) -> Methodology:
    return _read(Path(path))


def load_methodology(path: Path | None = None) -> Methodology:
    """Load and validate the v3 methodology. Only the default path is cached."""
    if path is not None:
        return _read(Path(path))
    return _load_default(str(os.getenv("AUDIT_METHODOLOGY_V3_PATH") or DEFAULT_CONFIG_PATH))


load_methodology.cache_clear = _load_default.cache_clear  # type: ignore[attr-defined]
