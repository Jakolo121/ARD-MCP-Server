"""
Token-bucket rate limiter.

Single Responsibility: decide whether one more upstream request may be
sent right now. No I/O, no sleeping, no retries — a denied request is
the caller's problem to report.
"""

import time
from typing import Callable


class TokenBucketRateLimiter:
    """Token bucket that starts full, refills continuously, never blocks.

    The bucket holds at most ``capacity`` tokens and refills at a constant
    rate of ``capacity / refill_period_seconds`` tokens per second.
    """

    def __init__(
        self,
        capacity: int,
        refill_period_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """
        Args:
            capacity: Maximum requests per refill period (bucket size).
            refill_period_seconds: Time to refill a full bucket (default 1 h).
            clock: Monotonic time source in seconds — injectable for tests.
        """
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        if refill_period_seconds <= 0:
            raise ValueError(
                f"refill_period_seconds must be > 0, got {refill_period_seconds}"
            )
        self._capacity = capacity
        self._refill_rate = capacity / refill_period_seconds
        self._clock = clock
        self._tokens = float(capacity)
        self._last_refill = clock()

    @property
    def capacity(self) -> int:
        """Bucket size (maximum requests per refill period)."""
        return self._capacity

    def try_acquire(self) -> bool:
        """Take one token. Returns False when the bucket is empty. Never blocks."""
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(
            float(self._capacity),
            self._tokens + elapsed * self._refill_rate,
        )
