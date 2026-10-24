"""In-memory token bucket per (user, action) (T-EN09.3). One bucket set per API replica; the reverse proxy adds a
second, coarse limit (`limit_req`) in front of all replicas."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    updated: float


class RateLimiter:
    def __init__(self, *, capacity: int, per_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._capacity = capacity
        self._rate = capacity / per_seconds  # tokens per second
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    def acquire(self, key: str) -> float:
        """Takes one token. Returns 0 when allowed, otherwise the seconds to wait before retrying."""
        now = self._clock()
        b = self._buckets.get(key)
        if b is None:
            b = self._buckets[key] = _Bucket(self._capacity, now)
        b.tokens = min(self._capacity, b.tokens + (now - b.updated) * self._rate)
        b.updated = now
        if b.tokens >= 1:
            b.tokens -= 1
            return 0.0
        return (1 - b.tokens) / self._rate


def seconds(wait: float) -> int:
    """Whole seconds for the Retry-After header / the FE message."""
    return max(1, math.ceil(wait))
