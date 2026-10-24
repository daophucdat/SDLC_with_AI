"""Q&A persistence (T302.4) and the cross-replica stop signal (T310.1). Schema: qa.* in 0001_init."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import text as sql
from sqlalchemy.ext.asyncio import AsyncEngine

from chatdocs.domain.qa.citation_policy import Citation
from chatdocs.domain.qa.question import AnswerStatus, NotFoundReason, Question, Turn
from chatdocs.platform.logging import get_logger
from chatdocs.ports.qa import AnswerRecord, Conversation

log = get_logger("chatdocs.qa")
STOP_CHANNEL = "answer_stop"


class PgQaRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def create_conversation(self, conversation: Conversation, now: datetime) -> None:
        async with self._e.begin() as c:
            await c.execute(
                sql("INSERT INTO qa.conversation (id, session_id, user_id, started_at) VALUES (:id, :s, :u, :now)"),
                {"id": conversation.id, "s": conversation.session_id_hash, "u": conversation.user_id, "now": now},
            )

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    sql("SELECT id, session_id, user_id FROM qa.conversation WHERE id = :id"), {"id": conversation_id}
                )
            ).first()
        return Conversation(row.id, bytes(row.session_id), row.user_id) if row else None

    async def save_question_and_answer(self, question: Question, answer_id: UUID) -> None:
        q = question
        async with self._e.begin() as c:
            await c.execute(
                sql("""
                INSERT INTO qa.question (id, conversation_id, text, language, is_followup, asked_at)
                VALUES (:id, :conv, :t, :lang, :fu, :at)"""),
                {
                    "id": q.id,
                    "conv": q.conversation_id,
                    "t": q.text,
                    "lang": q.language.value,
                    "fu": q.is_followup,
                    "at": q.asked_at,
                },
            )
            await c.execute(
                sql("INSERT INTO qa.answer (id, question_id, status) VALUES (:id, :q, 'STREAMING')"),
                {"id": answer_id, "q": q.id},
            )

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
    ) -> None:
        async with self._e.begin() as c:
            await c.execute(
                sql("""
                UPDATE qa.answer SET status = 'COMPLETED', text = :t, latency_ms = :lat, first_token_ms = :ft,
                                     model_id = :m, completed_at = :now
                 WHERE id = :id AND status = 'STREAMING'"""),
                {"id": answer_id, "t": text, "lat": latency_ms, "ft": first_token_ms, "m": model_id, "now": now},
            )
            if citations:
                await c.execute(
                    sql("""
                    INSERT INTO qa.citation (answer_id, idx, chunk_id, document_id, file_name, page_number, excerpt)
                    VALUES (:a, :i, :ch, :d, :f, :p, :e)"""),
                    [
                        {
                            "a": answer_id,
                            "i": ci.index,
                            "ch": ci.chunk_id,
                            "d": ci.document_id,
                            "f": ci.file_name,
                            "p": ci.page_number,
                            "e": ci.excerpt,
                        }
                        for ci in citations
                    ],
                )

    async def _finish(self, answer_id: UUID, status: str, **fields) -> None:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        async with self._e.begin() as c:
            await c.execute(
                sql(f"UPDATE qa.answer SET status = :st, {sets} WHERE id = :id AND status = 'STREAMING'"),
                {"id": answer_id, "st": status, **fields},
            )

    async def mark_not_found(
        self, answer_id: UUID, reason: NotFoundReason, *, latency_ms: int, first_token_ms: int | None, now: datetime
    ) -> None:
        # The streamed text (if any) is not kept: a NOT_FOUND answer must not show model text (EC-14).
        await self._finish(
            answer_id,
            "NOT_FOUND",
            text="",
            not_found_reason=reason.value,
            latency_ms=latency_ms,
            first_token_ms=first_token_ms,
            completed_at=now,
        )

    async def mark_failed(self, answer_id: UUID, *, latency_ms: int, now: datetime) -> None:
        await self._finish(answer_id, "FAILED", latency_ms=latency_ms, completed_at=now)

    async def mark_stopped(self, answer_id: UUID, *, partial_text: str, latency_ms: int, now: datetime) -> None:
        await self._finish(answer_id, "STOPPED", text=partial_text, latency_ms=latency_ms, completed_at=now)

    async def get_answer(self, answer_id: UUID) -> AnswerRecord | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    sql("""
                SELECT a.id, a.question_id, a.status, q.conversation_id, cv.user_id, cv.session_id
                  FROM qa.answer a JOIN qa.question q ON q.id = a.question_id
                  JOIN qa.conversation cv ON cv.id = q.conversation_id
                 WHERE a.id = :id"""),
                    {"id": answer_id},
                )
            ).first()
        if not row:
            return None
        return AnswerRecord(
            row.id, row.question_id, row.conversation_id, row.user_id, bytes(row.session_id), AnswerStatus(row.status)
        )

    async def turns(self, conversation_id: UUID, limit: int | None = None) -> list[Turn]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    sql("""
                SELECT q.id AS qid, q.text AS qtext, a.id AS aid, a.text AS atext, a.status, f.value AS feedback
                  FROM qa.question q JOIN qa.answer a ON a.question_id = q.id
                  LEFT JOIN qa.feedback f ON f.answer_id = a.id
                 WHERE q.conversation_id = :c
                 ORDER BY q.asked_at"""),
                    {"c": conversation_id},
                )
            ).all()
            if limit:
                rows = rows[-limit:]
            answer_ids = [r.aid for r in rows]
            cites = (
                (
                    await c.execute(
                        sql("""
                    SELECT ci.answer_id, ci.idx, ci.chunk_id, ci.document_id, ci.file_name, ci.page_number, ci.excerpt,
                           (d.removed_at IS NOT NULL) AS removed
                      FROM qa.citation ci JOIN documents.document d ON d.id = ci.document_id
                     WHERE ci.answer_id = ANY(:ids) ORDER BY ci.answer_id, ci.idx"""),
                        {"ids": answer_ids},
                    )
                ).all()
                if answer_ids
                else []
            )
        by_answer: dict[UUID, list[Citation]] = {}
        for r in cites:
            by_answer.setdefault(r.answer_id, []).append(
                Citation(r.idx, r.chunk_id, r.document_id, r.file_name, r.page_number, r.excerpt, bool(r.removed))
            )
        return [
            Turn(r.qid, r.qtext, r.aid, r.atext, AnswerStatus(r.status), by_answer.get(r.aid, []), r.feedback)
            for r in rows
        ]

    async def save_feedback(self, answer_id: UUID, value: str, reason: str | None, now: datetime) -> bool:
        async with self._e.begin() as c:
            res = await c.execute(
                sql("""
                INSERT INTO qa.feedback (answer_id, value, reason, submitted_at) VALUES (:a, :v, :r, :now)
                ON CONFLICT (answer_id) DO NOTHING"""),
                {"a": answer_id, "v": value, "r": reason, "now": now},
            )
        return bool(res.rowcount)


class PgStopBus:
    """NOTIFY answer_stop '<answer id>'; every API replica LISTENs and sets the flag if it runs that stream."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine
        self._handlers: list[Callable[[UUID], Awaitable[None] | None]] = []
        self._listen_conn = None

    async def publish(self, answer_id: UUID) -> None:
        async with self._e.begin() as c:
            await c.execute(sql("SELECT pg_notify(:ch, :id)"), {"ch": STOP_CHANNEL, "id": str(answer_id)})

    def subscribe(self, handler: Callable[[UUID], Awaitable[None] | None]) -> None:
        self._handlers.append(handler)

    def _on_notify(self, _conn, _pid, _channel, payload: str) -> None:
        try:
            answer_id = UUID(payload)
        except ValueError:
            return
        for h in self._handlers:
            res = h(answer_id)
            if inspect.isawaitable(res):
                asyncio.ensure_future(res)

    async def start(self) -> None:
        self._listen_conn = await self._e.connect()
        raw = await self._listen_conn.get_raw_connection()
        await raw.driver_connection.add_listener(STOP_CHANNEL, self._on_notify)

    async def close(self) -> None:
        if self._listen_conn is not None:
            await self._listen_conn.close()


class LocalStopBus:
    """Single-process stand-in (tests, one replica)."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[UUID], Awaitable[None] | None]] = []
        self.published: list[UUID] = []

    async def publish(self, answer_id: UUID) -> None:
        self.published.append(answer_id)
        for h in self._handlers:
            res = h(answer_id)
            if inspect.isawaitable(res):
                await res

    def subscribe(self, handler: Callable[[UUID], Awaitable[None] | None]) -> None:
        self._handlers.append(handler)
