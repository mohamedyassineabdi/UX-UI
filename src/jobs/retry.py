from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class TransientJobError(RuntimeError):
    """A retryable infrastructure failure, never an input/authentication failure."""


def retry_transient(operation: Callable[[], T], *, attempts: int = 2, delay: Callable[[float], None] = time.sleep, base_delay: float = 0.1) -> T:
    """Retry only the explicitly classified transient operation a bounded number of times."""
    if attempts < 1:
        raise ValueError("attempts must be at least one.")
    for attempt in range(attempts):
        try:
            return operation()
        except TransientJobError:
            if attempt + 1 == attempts:
                raise
            delay(base_delay * (2**attempt))
    raise AssertionError("unreachable")
