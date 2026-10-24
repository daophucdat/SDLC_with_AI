from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from chatdocs.domain.qa.citation_policy import Citation
from chatdocs.domain.qa.question import AnswerStatus, NotFoundReason, Question, Turn


@dataclass(frozen=True)
class Conversation:
    id: UUID
    session_id_hash: bytes
    user_id: UUID


@dataclass(frozen=True)
class AnswerRecord:
    id: UUID
    question_id: UUID
    conversation_id: UUID
    user_id: UUID
    session_id_hash: bytes
    status: AnswerStatus


class QaRepository(Protocol):
    async def create_conversation(self, conversation: Conversation, now: datetime) -> None: ...

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None: ...

    async def save_question_and_answer(self, question: Question, answer_id: UUID) -> None:
        """One transaction: question row + answer row in STREAMING."""
        ...

    async def complete(
        self,
        answer_id: UUID,
        *,
        text: str,
        citations: list[Citation],
        latency_ms: int,
        first_token_ms: int | None,
        model_id: str,
        now: datetime,
    ) -> None: ...

    async def mark_not_found(
        self, answer_id: UUID, reason: NotFoundReason, *, latency_ms: int, first_token_ms: int | None, now: datetime
    ) -> None: ...

    async def mark_failed(self, answer_id: UUID, *, latency_ms: int, now: datetime) -> None: ...

    async def mark_stopped(self, answer_id: UUID, *, partial_text: str, latency_ms: int, now: datetime) -> None: ...

    async def get_answer(self, answer_id: UUID) -> AnswerRecord | None: ...

    async def turns(self, conversation_id: UUID, limit: int | None = None) -> list[Turn]:
        """Oldest first; `limit` keeps the most recent turns."""
        ...

    async def save_feedback(self, answer_id: UUID, value: str, reason: str | None, now: datetime) -> bool:
        """INSERT … ON CONFLICT DO NOTHING; False if feedback already existed."""
        ...


class AnalyticsSink(Protocol):
    """Fire-and-forget: never raises, never blocks a request (T-EN08.2)."""

    def emit(self, name: str, props: dict[str, Any], *, user_id: UUID | None, session_id: str | None) -> None: ...


class StopBus(Protocol):
    """Cross-replica stop signal (T310.1): the replica running the stream may not be the one receiving the stop."""

    async def publish(self, answer_id: UUID) -> None: ...

    def subscribe(self, handler: Callable[[UUID], Awaitable[None] | None]) -> None: ...
