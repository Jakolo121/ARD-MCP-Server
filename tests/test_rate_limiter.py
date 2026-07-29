"""
Tests for german_newsfeed_mcp.rate_limiter — token bucket logic.

All tests use an injected fake clock; no sleeping, no wall-clock time.
"""

import pytest

from german_newsfeed_mcp.rate_limiter import TokenBucketRateLimiter


class FakeClock:
    """Deterministic, manually advanced time source."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTokenBucketRateLimiter:
    """Unit tests for TokenBucketRateLimiter."""

    def test_bucket_starts_full(self):
        """A fresh bucket must grant exactly <capacity> tokens."""
        limiter = TokenBucketRateLimiter(capacity=5, clock=FakeClock())
        assert all(limiter.try_acquire() for _ in range(5))

    def test_acquire_beyond_capacity_is_denied(self):
        """The acquire following a drained bucket must be denied."""
        limiter = TokenBucketRateLimiter(capacity=5, clock=FakeClock())
        for _ in range(5):
            limiter.try_acquire()
        assert limiter.try_acquire() is False

    def test_denied_before_refill_interval(self):
        """With 60/h, less than 60 s after draining no token is available."""
        clock = FakeClock()
        limiter = TokenBucketRateLimiter(capacity=60, clock=clock)
        for _ in range(60):
            assert limiter.try_acquire()
        clock.advance(59.0)  # < 60 s → less than one token refilled
        assert limiter.try_acquire() is False

    def test_refill_grants_one_token(self):
        """With 60/h, one token must be back after just over 60 s."""
        clock = FakeClock()
        limiter = TokenBucketRateLimiter(capacity=60, clock=clock)
        for _ in range(60):
            limiter.try_acquire()
        clock.advance(61.0)  # > 60 s → exactly one token refilled
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_refill_never_exceeds_capacity(self):
        """A long idle period must not stack up more than <capacity> tokens."""
        clock = FakeClock()
        limiter = TokenBucketRateLimiter(capacity=3, clock=clock)
        clock.advance(1_000_000.0)
        for _ in range(3):
            assert limiter.try_acquire()
        assert limiter.try_acquire() is False

    def test_custom_refill_period(self):
        """The refill rate must follow capacity / refill_period_seconds."""
        clock = FakeClock()
        limiter = TokenBucketRateLimiter(
            capacity=2, refill_period_seconds=10.0, clock=clock
        )
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.try_acquire() is False
        clock.advance(6.0)  # 6 s * (2 tokens / 10 s) = 1.2 tokens
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_capacity_property(self):
        """The capacity property must expose the configured bucket size."""
        limiter = TokenBucketRateLimiter(capacity=42, clock=FakeClock())
        assert limiter.capacity == 42

    @pytest.mark.parametrize("capacity", [0, -1])
    def test_invalid_capacity_raises(self, capacity):
        """A capacity below 1 must raise ValueError."""
        with pytest.raises(ValueError):
            TokenBucketRateLimiter(capacity=capacity, clock=FakeClock())

    def test_invalid_refill_period_raises(self):
        """A refill period of 0 must raise ValueError."""
        with pytest.raises(ValueError):
            TokenBucketRateLimiter(
                capacity=1, refill_period_seconds=0, clock=FakeClock()
            )
