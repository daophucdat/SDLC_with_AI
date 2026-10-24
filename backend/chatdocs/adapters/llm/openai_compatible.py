"""AnswerGenerator for a self-hosted model behind an OpenAI-compatible /v1/chat/completions endpoint (vLLM, TGI) —
the internal-hosting option of OQ-008. Same port as the Claude adapter; selected with LLM_PROVIDER=openai_compatible."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from chatdocs.adapters.llm.resilient import RetryableProviderError
from chatdocs.domain.qa.prompt import Prompt
from chatdocs.ports.answer_generator import GenerationStats, GenerationUnavailable


class OpenAICompatibleGenerator:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        max_output_tokens: int = 800,
        connect_timeout_s: float = 3,
        read_timeout_s: float = 28,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._model, self._max_tokens = model, max_output_tokens
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(read_timeout_s, connect=connect_timeout_s),
            transport=transport,
        )

    async def stream(self, prompt: Prompt, cancel: asyncio.Event, stats: GenerationStats) -> AsyncIterator[str]:
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": 0,
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}],
        }
        try:
            async with self._http.stream("POST", "/v1/chat/completions", json=body) as resp:
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise RetryableProviderError(f"status_{resp.status_code}")
                if resp.status_code >= 400:
                    raise GenerationUnavailable(f"status_{resp.status_code}")
                stats.model_id = self._model
                async for line in resp.aiter_lines():
                    if cancel.is_set():
                        break
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    if usage := event.get("usage"):
                        stats.input_tokens = usage.get("prompt_tokens", 0)
                        stats.output_tokens = usage.get("completion_tokens", 0)
                    for choice in event.get("choices") or []:
                        if piece := (choice.get("delta") or {}).get("content"):
                            yield piece
        except httpx.TransportError as e:
            raise RetryableProviderError("connection") from e
