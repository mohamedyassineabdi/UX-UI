"""Shared Phase 3B measurement taxonomy and conservative accessibility helpers."""
from __future__ import annotations

from typing import Any

MEASUREMENT_CLASSES = {"standards_automated", "browser_runtime", "deterministic_custom", "heuristic_custom", "ai_visual", "ai_interpretation"}


def measurement_metadata(method: str, measurement_class: str, *, limitations: list[str] | None = None) -> dict[str, Any]:
    if measurement_class not in MEASUREMENT_CLASSES:
        raise ValueError("Unknown measurement class.")
    return {"measurementMethod": method, "measurementClass": measurement_class, "limitations": limitations or []}


def valid_accessible_name(element: dict[str, Any]) -> str:
    """Diagnostic fallback only; IDs, hrefs, tags and XPath are never names."""
    for key in ("accessibleName", "ariaLabel", "ariaLabelledByText", "label", "text", "alt", "title"):
        value = " ".join(str(element.get(key) or "").split())
        if value:
            return value
    return ""


def target_size_assessment(element: dict[str, Any]) -> dict[str, str]:
    rect = element.get("rect") or {}
    width, height = float(rect.get("width") or 0), float(rect.get("height") or 0)
    if str(element.get("tag") or "").lower() == "a" and bool(element.get("inlineText")):
        return {"state": "unknown", "reason": "inline_text_exception_needs_review"}
    if width >= 24 and height >= 24:
        return {"state": "pass", "reason": "minimum_24_css_px"}
    if element.get("sufficientSpacing") is True:
        return {"state": "pass", "reason": "spacing_exception"}
    if element.get("sufficientSpacing") is None:
        return {"state": "unknown", "reason": "spacing_exception_not_measured"}
    return {"state": "fail", "reason": "below_24_css_px_without_spacing_exception"}


def contrast_assessment(element: dict[str, Any]) -> dict[str, Any]:
    if element.get("complexBackground"):
        return {"measurement": "not_measured", "reason": "complex_background"}
    ratio = element.get("contrastAgainstEffectiveBackground")
    if ratio is None:
        return {"measurement": "not_measured", "reason": "background_not_resolved"}
    large = bool(element.get("isLargeText"))
    threshold = 3.0 if large else 4.5
    return {"measurement": "measured", "ratio": float(ratio), "threshold": threshold, "state": "pass" if float(ratio) >= threshold else "fail"}
