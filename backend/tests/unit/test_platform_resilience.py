"""EN-06 circuit breaker, timeouts, retry; EN-09 rate limiting."""

from __future__ import annotations

import asyncio

import pytest

from chatdocs.adapters.llm.resilient import ResilientGenerator, RetryableProviderError
from chatdocs.domain.qa.prompt import Prompt
from chatdocs.platform.circuit_breaker import CircuitBreaker, CircuitOpen, CircuitState
from chatdocs.platform.rate_limit import RateLimiter, seconds
from chatdocs.ports.answer_generator import GenerationStats, GenerationTimeout, GenerationUnavailable

PROMPT = Prompt("v1", "sys", "Câu hỏi: x", [])


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_breaker_opens_after_consecutive_failures_then_half_opens_once():
    clock = Clock()
    seen = []
    b = CircuitBreaker(consecutive=5, min_calls=100, open_seconds=30, clock=clock, on_state=seen.append)
    for _ in range(5):
        b.before_call()
        b.record(False)
    assert b.state is CircuitState.OPEN
    with pytest.raises(CircuitOpen):
        b.before_call()
    clock.t = 31
    assert b.state is CircuitState.HALF_OPEN
    b.before_call()  # the single trial call
    with pytest.raises(CircuitOpen):
        b.before_call()  # a second concurrent call is refused while the trial runs
    b.record(True)
    assert b.state is CircuitState.CLOSED
    assert seen == [CircuitState.OPEN, CircuitState.HALF_OPEN, CircuitState.CLOSED]


def test_breaker_opens_on_failure_ratio_within_window():
    clock = Clock()
    b = CircuitBreaker(failure_ratio=0.5, min_calls=10, consecutive=99, window_seconds=60, clock=clock)
    for i in range(10):
        b.record(i % 2 == 0)  # 50 % failures, never 5 in a row
    assert b.state is CircuitState.OPEN


def test_breaker_forgets_calls_outside_the_window():
    clock = Clock()
    b = CircuitBreaker(failure_ratio=0.5, min_calls=4, consecutive=99, window_seconds=60, clock=clock)
    for _ in range(3):
        b.record(False)
    clock.t = 120
    for _ in range(3):
        b.record(True)
    b.record(False)
    assert b.state is CircuitState.CLOSED


def test_failed_trial_reopens():
    clock = Clock()
    b = CircuitBreaker(consecutive=1, open_seconds=10, clock=clock)
    b.record(False)
    clock.t = 11
    b.before_call()
    b.record(False)
    assert b.state is CircuitState.OPEN


def test_rate_limiter_token_bucket():
    clock = Clock()
    rl = RateLimiter(capacity=10, per_seconds=60, clock=clock)
    assert all(rl.acquire("u1") == 0 for _ in range(10))
    wait = rl.acquire("u1")
    assert 5.9 < wait <= 6.0 and seconds(wait) == 6
    assert rl.acquire("u2") == 0  # per user
    clock.t = 6.1
    assert rl.acquire("u1") == 0


# ---------------------------------------------------------------- ResilientGenerator
class Scripted:
    def __init__(self, plan):
        self.plan, self.calls = list(plan), 0

    async def stream(self, prompt, cancel, stats):
        self.calls += 1
        step = self.plan.pop(0)
        for item in step:
            if isinstance(item, Exception):
                raise item
            if isinstance(item, float):
                await asyncio.sleep(item)
                continue
            yield item


async def collect(gen):
    return [p async for p in gen.stream(PROMPT, asyncio.Event(), GenerationStats())]


async def test_retries_once_before_first_token():
    inner = Scripted([[RetryableProviderError("503")], ["Xin ", "chào"]])
    gen = ResilientGenerator(inner, retry_backoff_s=0, sleep=lambda s: asyncio.sleep(0))
    assert await collect(gen) == ["Xin ", "chào"]
    assert inner.calls == 2


async def test_no_second_retry():
    inner = Scripted([[RetryableProviderError("503")], [RetryableProviderError("503")]])
    gen = ResilientGenerator(inner, retry_backoff_s=0, sleep=lambda s: asyncio.sleep(0))
    with pytest.raises(GenerationUnavailable):
        await collect(gen)
    assert inner.calls == 2


async def test_no_retry_after_first_token():
    inner = Scripted([["Xin ", RetryableProviderError("conn")], ["never"]])
    gen = ResilientGenerator(inner, retry_backoff_s=0, sleep=lambda s: asyncio.sleep(0))
    with pytest.raises(GenerationUnavailable):
        await collect(gen)
    assert inner.calls == 1


async def test_first_token_timeout():
    gen = ResilientGenerator(Scripted([[1.0, "late"]]), first_token_timeout_s=0.05, total_timeout_s=5)
    with pytest.raises(GenerationTimeout):
        await collect(gen)


async def test_total_deadline():
    gen = ResilientGenerator(
        Scripted([["a", 0.04, "b", 0.04, "c", 0.04, "d"]]), first_token_timeout_s=1, total_timeout_s=0.1
    )
    with pytest.raises(GenerationTimeout):
        await collect(gen)


def test_spans_never_record_text(monkeypatch):
    """T-EN07.3: only numbers / booleans become span attributes."""
    from chatdocs.platform import tracing

    recorded = {}

    class Span:
        def end(self):
            pass

    class Tracer:
        def start_span(self, name, attributes):
            recorded.update(attributes)
            return Span()

    monkeypatch.setattr(tracing, "_tracer", Tracer())
    with tracing.span("llm.stream", chunks=3, latency_ms=12.5, ok=True, question="ZZZ-SECRET", prompt="x"):
        pass
    assert recorded == {"chunks": 3, "latency_ms": 12.5, "ok": True}
