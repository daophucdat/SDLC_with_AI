"""Circuit breaker for the LLM (T-EN06.6, SAD §4.2). Opens on a failure ratio over a sliding window or on N
consecutive failures, stays open for `open_seconds`, then lets exactly one trial call through (half-open)."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_ratio: float = 0.5,
        min_calls: int = 10,
        window_seconds: float = 60,
        consecutive: int = 5,
        open_seconds: float = 30,
        clock: Callable[[], float] = time.monotonic,
        on_state: Callable[[CircuitState], None] | None = None,
    ) -> None:
        self._ratio, self._min, self._window = failure_ratio, min_calls, window_seconds
        self._consecutive_limit, self._open_s, self._clock = consecutive, open_seconds, clock
        self._calls: deque[tuple[float, bool]] = deque()  # (time, ok)
        self._consecutive = 0
        self._opened_at: float | None = None
        self._trial_in_flight = False
        self._on_state = on_state
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        if self._state is CircuitState.OPEN and self._clock() - (self._opened_at or 0) >= self._open_s:
            self._set(CircuitState.HALF_OPEN)
        return self._state

    def _set(self, state: CircuitState) -> None:
        if state is not self._state:
            self._state = state
            if self._on_state:
                self._on_state(state)

    def before_call(self) -> None:
        """Raises CircuitOpen when the call must not be attempted."""
        st = self.state
        if st is CircuitState.OPEN:
            raise CircuitOpen()
        if st is CircuitState.HALF_OPEN:
            if self._trial_in_flight:
                raise CircuitOpen()
            self._trial_in_flight = True

    def record(self, ok: bool) -> None:
        now = self._clock()
        if self._state is CircuitState.HALF_OPEN:
            self._trial_in_flight = False
            if ok:
                self._calls.clear()
                self._consecutive = 0
                self._set(CircuitState.CLOSED)
            else:
                self._trip(now)
            return
        self._calls.append((now, ok))
        while self._calls and self._calls[0][0] < now - self._window:
            self._calls.popleft()
        self._consecutive = 0 if ok else self._consecutive + 1
        failures = sum(1 for _, good in self._calls if not good)
        if self._consecutive >= self._consecutive_limit or (
            len(self._calls) >= self._min and failures / len(self._calls) >= self._ratio
        ):
            self._trip(now)

    def _trip(self, now: float) -> None:
        self._opened_at = now
        self._set(CircuitState.OPEN)
