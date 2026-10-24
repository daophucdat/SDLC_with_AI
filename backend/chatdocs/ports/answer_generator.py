from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol

from chatdocs.domain.qa.prompt import Prompt


class GenerationTimeout(Exception):
    """No first token in time, or the total deadline passed (T-EN06.4) → SSE error AI_TIMEOUT."""


class GenerationUnavailable(Exception):
    """Provider down, circuit open or non-retryable provider error → SSE error AI_UNAVAILABLE."""


@dataclass
class GenerationStats:
    """Filled in by the adapter while streaming; read by the service after the stream ends."""

    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    extra: dict = field(default_factory=dict)


class AnswerGenerator(Protocol):
    """IF-04 (T-EN06.1). Yields text pieces. Must stop promptly (and stop paying for tokens) once `cancel` is set."""

    async def stream(self, prompt: Prompt, cancel: asyncio.Event, stats: GenerationStats) -> AsyncIterator[str]: ...
