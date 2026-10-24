"""AnswerGenerator on the Claude API (T-EN06.2), official `anthropic` SDK, streaming.

SEC-04 / LG-12: the organisation's API account must be configured for no training and minimum retention; that is a
contract setting on the provider side, not a request flag — see docs/implement/reports/launch_gates.md (LG-12)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import anthropic

from chatdocs.adapters.llm.resilient import RetryableProviderError
from chatdocs.domain.qa.prompt import Prompt
from chatdocs.ports.answer_generator import GenerationStats, GenerationUnavailable

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicAnswerGenerator:
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        base_url: str | None = None,
        max_output_tokens: int = 800,
        connect_timeout_s: float = 3,
        read_timeout_s: float = 28,
        effort: str = "low",
        refusal_fallback: bool = True,
    ) -> None:
        self._model, self._max_tokens, self._effort = model, max_output_tokens, effort
        self._fallback = refusal_fallback
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,  # ResilientGenerator owns the retry policy (one retry, before the first token only)
            timeout=anthropic.Timeout(read_timeout_s, connect=connect_timeout_s),
        )

    def _request(self, prompt: Prompt) -> dict:
        req = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": prompt.system,
            "messages": [{"role": "user", "content": prompt.user}],
            # Short factual answers: low effort keeps the first token fast (NFR-02). Sampling parameters
            # (temperature) are not sent — current models reject non-default values.
            "output_config": {"effort": self._effort},
        }
        if self._fallback:
            req["betas"] = [FALLBACK_BETA]
            req["fallbacks"] = "default"
        return req

    async def stream(self, prompt: Prompt, cancel: asyncio.Event, stats: GenerationStats) -> AsyncIterator[str]:
        req = self._request(prompt)
        client = self._client.beta.messages if self._fallback else self._client.messages
        try:
            async with client.stream(**req) as s:
                async for text in s.text_stream:
                    if cancel.is_set():
                        break  # leaving the context manager closes the HTTP stream → no more tokens billed
                    yield text
                if not cancel.is_set():
                    final = await s.get_final_message()
                    stats.model_id = final.model
                    stats.input_tokens = final.usage.input_tokens
                    stats.output_tokens = final.usage.output_tokens
                    stats.extra["stop_reason"] = final.stop_reason
                else:
                    stats.model_id = self._model
        except anthropic.RateLimitError as e:
            raise RetryableProviderError("rate_limited") from e
        except anthropic.APIConnectionError as e:  # includes APITimeoutError
            raise RetryableProviderError("connection") from e
        except anthropic.APIStatusError as e:
            if e.status_code in (500, 502, 503, 504, 529):
                raise RetryableProviderError(f"status_{e.status_code}") from e
            raise GenerationUnavailable(f"status_{e.status_code}") from e
