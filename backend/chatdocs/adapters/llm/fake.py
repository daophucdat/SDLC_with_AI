"""Scripted AnswerGenerator for tests, CI E2E and dev without an API key (T-EN06.3).

The scenario is chosen from markers in the question (last line of the prompt):
- "#notfound" → NOT_FOUND token          - "#badref" → cites a chunk number that does not exist
- "#noref"    → answer without citations - "#slow"   → waits 40 s before the first token
- "#503"      → provider error (retryable) - "#hang"  → first token, then hangs
Otherwise it answers from the context: the first sentence of chunk 1 (and chunk 2 if present), each cited,
in the question's language (Vietnamese system prompt rule 5 decides)."""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator

from chatdocs.adapters.llm.resilient import RetryableProviderError
from chatdocs.domain.qa.prompt import Prompt
from chatdocs.ports.answer_generator import GenerationStats

_SENTENCE = re.compile(r"(.+?[.!?])(\s|$)", re.S)


def _first_sentence(text: str, limit: int = 220) -> str:
    m = _SENTENCE.search(text.strip())
    return (m.group(1) if m else text.strip())[:limit].strip()


class FakeAnswerGenerator:
    def __init__(self, *, piece_chars: int = 12, delay_s: float = 0.0) -> None:
        self.calls = 0
        self._piece, self._delay = piece_chars, delay_s
        self.last_prompt: Prompt | None = None

    def script(self, prompt: Prompt) -> str:
        question = prompt.user.rsplit("Câu hỏi:", 1)[-1].lower()
        if "#notfound" in question or not prompt.chunks:
            return "NOT_FOUND"
        if "#badref" in question:
            return f"Theo tài liệu, giá trị là 30% [{len(prompt.chunks) + 5}]."
        if "#noref" in question:
            return "Theo tài liệu, khách hàng thanh toán 30% khi ký hợp đồng."
        english = "tiếng Anh" in prompt.system
        lead = "According to the documents: " if english else "Theo tài liệu: "
        parts = [f"{_first_sentence(prompt.chunks[0].content)} [1]"]
        if len(prompt.chunks) > 1 and prompt.chunks[1].document_id != prompt.chunks[0].document_id:
            parts.append(f"{_first_sentence(prompt.chunks[1].content)} [2]")
        return lead + "\n\n".join(parts)

    async def stream(self, prompt: Prompt, cancel: asyncio.Event, stats: GenerationStats) -> AsyncIterator[str]:
        self.calls += 1
        self.last_prompt = prompt
        stats.model_id = "fake-llm"
        question = prompt.user.rsplit("Câu hỏi:", 1)[-1].lower()
        if "#503" in question:
            raise RetryableProviderError("status_503")
        if "#slow" in question:
            await asyncio.sleep(40)
        text = self.script(prompt)
        stats.input_tokens = prompt.estimated_tokens()
        for i in range(0, len(text), self._piece):
            if cancel.is_set():
                return
            if self._delay:
                await asyncio.sleep(self._delay)
            stats.output_tokens += 1
            yield text[i : i + self._piece]
            if "#hang" in question:
                await asyncio.sleep(3600)
