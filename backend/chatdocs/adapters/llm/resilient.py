"""Timeouts and retry around any provider adapter (T-EN06.4, T-EN06.5).

- no first token after `first_token_timeout_s` → GenerationTimeout
- whole answer must finish before `request_start + total_timeout_s` → GenerationTimeout
- one retry, only before the first token, only for connection / 429 / 503-type errors, backoff 300 ms ± jitter"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator

from chatdocs.domain.qa.prompt import Prompt
from chatdocs.ports.answer_generator import AnswerGenerator, GenerationStats, GenerationTimeout, GenerationUnavailable


class RetryableProviderError(Exception):
    """Raised by provider adapters for failures worth one retry before the first token."""


class ResilientGenerator:
    def __init__(
        self,
        inner: AnswerGenerator,
        *,
        first_token_timeout_s: float = 10,
        total_timeout_s: float = 28,
        retry_backoff_s: float = 0.3,
        sleep=asyncio.sleep,
    ) -> None:
        self._inner, self._first, self._total = inner, first_token_timeout_s, total_timeout_s
        self._backoff, self._sleep = retry_backoff_s, sleep

    async def stream(self, prompt: Prompt, cancel: asyncio.Event, stats: GenerationStats) -> AsyncIterator[str]:
        deadline = time.monotonic() + self._total
        for attempt in (1, 2):
            gen = self._inner.stream(prompt, cancel, stats).__aiter__()
            got_token = False
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise GenerationTimeout("total deadline")
                    limit = remaining if got_token else min(remaining, self._first)
                    try:
                        piece = await asyncio.wait_for(gen.__anext__(), timeout=limit)
                    except StopAsyncIteration:
                        return
                    except asyncio.TimeoutError:
                        raise GenerationTimeout("first token" if not got_token else "total deadline") from None
                    got_token = True
                    yield piece
            except RetryableProviderError as e:
                if got_token or attempt == 2:
                    raise GenerationUnavailable(str(e)) from e
                await self._sleep(self._backoff * random.uniform(0.8, 1.2))  # noqa: S311 — jitter, not crypto
            finally:
                await _close(gen)
        raise GenerationUnavailable("unreachable")  # pragma: no cover


async def _close(gen) -> None:
    aclose = getattr(gen, "aclose", None)
    if aclose:
        try:
            await aclose()
        except Exception:  # noqa: BLE001, S110 — closing a broken stream must not mask the real error
            pass
