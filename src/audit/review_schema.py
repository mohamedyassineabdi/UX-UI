"""Strict, text-only human review payload validation."""
from __future__ import annotations

from typing import Any

ALLOWED_FINDING_FIELDS = {"reviewNote", "reviewedRecommendation", "priorityOverride", "reviewDecision", "suppressed", "suppressionReason"}
DECISIONS = {"accepted", "rejected", "adjusted", "needs_followup", "confirmed"}
PRIORITIES = {"low", "medium", "high", "critical"}


def _text(value: Any, name: str, limit: int, *, required: bool = False) -> str:
    if not isinstance(value, str):
        if required: raise ValueError(f"{name} is required.")
        return ""
    value = " ".join(value.split())
    if (required and not value) or len(value) > limit: raise ValueError(f"Invalid {name}.")
    return value


def validate_revision_payload(payload: dict[str, Any]) -> tuple[str | None, dict[str, Any], str]:
    expected = payload.get("expectedRevisionId")
    if expected is not None and (not isinstance(expected, str) or len(expected) != 32): raise ValueError("Invalid expectedRevisionId.")
    reason = _text(payload.get("reason"), "reason", 1000)
    raw = payload.get("findingChanges")
    if not isinstance(raw, dict) or not raw or len(raw) > 100: raise ValueError("findingChanges must contain 1 to 100 structured changes.")
    changes: dict[str, Any] = {}
    for finding_id, fields in raw.items():
        if not isinstance(finding_id, str) or not finding_id or len(finding_id) > 160 or not isinstance(fields, dict) or not fields: raise ValueError("Invalid finding change.")
        if set(fields) - ALLOWED_FINDING_FIELDS: raise ValueError("Machine-owned fields cannot be revised.")
        item: dict[str, Any] = {}
        for name in ("reviewNote", "reviewedRecommendation", "suppressionReason"):
            if name in fields: item[name] = _text(fields[name], name, 1200)
        if "priorityOverride" in fields:
            if fields["priorityOverride"] not in PRIORITIES: raise ValueError("Invalid priorityOverride.")
            item["priorityOverride"] = fields["priorityOverride"]
        if "reviewDecision" in fields:
            if fields["reviewDecision"] not in DECISIONS: raise ValueError("Invalid reviewDecision.")
            item["reviewDecision"] = fields["reviewDecision"]
        if "suppressed" in fields:
            if not isinstance(fields["suppressed"], bool): raise ValueError("suppressed must be boolean.")
            if fields["suppressed"] and not item.get("suppressionReason"): raise ValueError("Suppression requires a reason.")
            item["suppressed"] = fields["suppressed"]
        changes[finding_id] = item
    return expected, changes, reason
