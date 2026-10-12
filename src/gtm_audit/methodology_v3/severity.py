"""Methodology v3 severity levels and key-task escalation."""
from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """0 is the most severe."""
        return _ORDER.index(self)


_ORDER = (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW)


def escalate(severity: Severity, on_key_task: bool) -> tuple[Severity, bool]:
    """Raise a finding on a declared key-task path by one level (ceiling: critical)."""
    if not on_key_task or severity is Severity.CRITICAL:
        return severity, False
    return _ORDER[severity.rank - 1], True
