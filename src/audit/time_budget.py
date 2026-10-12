"""Audit time budget: an absolute deadline after which optional heavy steps are skipped.

The server sets UX_AUDIT_DEADLINE (epoch seconds) from the job start plus the
depth's budget. Core evidence (navigation, screenshot, DOM, axe) always runs;
heavy optional steps (click-tests, Lighthouse) are skipped once the budget is
spent or their per-depth page limit is reached, and the skip is recorded.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class TimeBudget:
    deadline: float | None
    clock: Callable[[], float] = field(default=time.time, compare=False)

    @classmethod
    def from_env(cls, clock: Callable[[], float] = time.time) -> "TimeBudget":
        raw = os.getenv("UX_AUDIT_DEADLINE", "").strip()
        try:
            return cls(float(raw) if raw else None, clock)
        except ValueError:
            return cls(None, clock)

    def remaining(self) -> float | None:
        return None if self.deadline is None else max(0.0, self.deadline - self.clock())

    def exhausted(self) -> bool:
        return self.deadline is not None and self.clock() >= self.deadline


def env_page_limit(name: str) -> int | None:
    """A positive per-step page limit from the environment, or None for no limit."""
    try:
        value = int(os.getenv(name, "").strip() or 0)
    except ValueError:
        return None
    return value if value > 0 else None


def heavy_step_skip_reason(page_index: int, page_limit: int | None, budget: TimeBudget) -> str | None:
    """Why a heavy optional step should be skipped for this page, or None to run it."""
    if page_limit is not None and page_index >= page_limit:
        return "page_limit"
    if budget.exhausted():
        return "time_budget"
    return None
