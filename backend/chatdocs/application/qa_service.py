"""QuestionAnsweringService — US-301 → US-304, US-306, US-308 → US-311 (dev_tasks.md Phần 3, §0.5).

Two phases so every HTTP error (400 / 409 / 429 / 503) is raised *before* the SSE stream opens:
`prepare()` validates and reserves an LLM slot, then `AskHandle.events()` produces the stream. The retrieval → LLM →
ALG-3 pipeline (`_pipeline`) is shared with the evaluation job (US-402), which runs it without persistence."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from chatdocs.application.access_service import AuthContext
from chatdocs.application.retrieval_service import RetrievalService
from chatdocs.domain.access.permissions import Action, can
from chatdocs.domain.errors import (
    AiBusy,
    AlreadySubmitted,
    Forbidden,
    InvalidState,
    NoReadyDocuments,
    QuestionInvalid,
    RateLimited,
    RouteNotFound,
)
from chatdocs.domain.ids import uuid7
from chatdocs.domain.qa import citation_policy
from chatdocs.domain.qa.citation_policy import Citation
from chatdocs.domain.qa.prompt import Prompt, build_search_query, build_v1
from chatdocs.domain.qa.question import AnswerStatus, Language, NotFoundReason, Question, Turn
from chatdocs.platform import metrics
from chatdocs.platform.circuit_breaker import CircuitBreaker, CircuitOpen, CircuitState
from chatdocs.platform.logging import get_logger
from chatdocs.platform.rate_limit import RateLimiter, seconds
from chatdocs.platform.tracing import span
from chatdocs.ports.answer_generator import (
    AnswerGenerator,
    GenerationStats,
    GenerationTimeout,
    GenerationUnavailable,
)
from chatdocs.ports.clock import Clock
from chatdocs.ports.qa import AnalyticsSink, Conversation, QaRepository, StopBus
from chatdocs.ports.repositories import DocumentRepository

log = get_logger("chatdocs.qa")

HOLD_BACK_CHARS = 16  # §0.5 rule 3: the NOT_FOUND token must never reach the screen
FEEDBACK_VALUES = {"HELPFUL", "NOT_HELPFUL"}
FEEDBACK_REASONS = {"wrong", "incomplete", "wrong_source", "other"}

SseEvent = tuple[str, dict[str, Any]]


@dataclass(frozen=True)
class QaConfig:
    context_tokens: int = 6000
    max_concurrency: int = 10
    queue_max: int = 20
    queue_wait_s: float = 5.0
    history_turns: int = 2
    followup_enabled: bool = False
    history_enabled: bool = False
    qa_off: bool = False  # REL-03 kill switch: FEATURE_FLAGS=…,qa_off turns Q&A off without a deploy


@dataclass
class PipelineOutcome:
    """What `_pipeline` decided; filled while it streams."""

    status: AnswerStatus | None = None
    reason: NotFoundReason | None = None
    text: str = ""
    citations: list[Citation] = field(default_factory=list)
    first_token_ms: int | None = None
    error_code: str | None = None
    stats: GenerationStats = field(default_factory=GenerationStats)


class LlmGate:
    """Per-replica concurrency limit + circuit breaker (T-EN06.6, T-EN06.7)."""

    def __init__(self, breaker: CircuitBreaker, max_concurrency: int, queue_max: int, wait_s: float) -> None:
        self.breaker = breaker
        self._sem = asyncio.Semaphore(max_concurrency)
        self._queue_max, self._wait_s, self._waiting = queue_max, wait_s, 0

    async def acquire(self) -> None:
        if self.breaker.state is CircuitState.OPEN:
            raise AiBusy(reason="circuit_open")
        if self._waiting >= self._queue_max:
            raise AiBusy(reason="queue_full")
        self._waiting += 1
        metrics.LLM_QUEUE.set(self._waiting)
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=self._wait_s)
        except asyncio.TimeoutError:
            raise AiBusy(reason="queue_timeout") from None
        finally:
            self._waiting -= 1
            metrics.LLM_QUEUE.set(self._waiting)

    def release(self) -> None:
        self._sem.release()


class QuestionAnsweringService:
    def __init__(
        self,
        *,
        qa: QaRepository,
        documents: DocumentRepository,
        retrieval: RetrievalService,
        llm: AnswerGenerator,
        gate: LlmGate,
        analytics: AnalyticsSink,
        stop_bus: StopBus,
        rate_limiter: RateLimiter,
        library_id: UUID,
        clock: Clock,
        config: QaConfig,
    ) -> None:
        self._qa, self._docs, self._retrieval, self._llm = qa, documents, retrieval, llm
        self._gate, self._analytics, self._bus = gate, analytics, stop_bus
        self._rate, self._library_id, self._clock, self.cfg = rate_limiter, library_id, clock, config
        self._stop_flags: dict[UUID, asyncio.Event] = {}
        stop_bus.subscribe(self._on_remote_stop)

    # ------------------------------------------------------------------ conversations
    async def start_conversation(self, auth: AuthContext) -> UUID:
        if not can(auth.user, Action.QA_ASK):
            raise Forbidden()
        conv = Conversation(uuid7(), auth.session_id_hash, auth.user.id)
        await self._qa.create_conversation(conv, self._clock.now())
        return conv.id

    async def _own_conversation(self, auth: AuthContext, conversation_id: UUID) -> Conversation:
        conv = await self._qa.get_conversation(conversation_id)
        # PD-04: a conversation belongs to one session; other sessions (even of the same user) cannot see it.
        if conv is None or conv.session_id_hash != auth.session_id_hash:
            raise RouteNotFound()
        return conv

    async def history(self, auth: AuthContext, conversation_id: UUID) -> list[Turn]:
        await self._own_conversation(auth, conversation_id)
        return await self._qa.turns(conversation_id)

    # ------------------------------------------------------------------ ask
    async def prepare(
        self,
        auth: AuthContext,
        conversation_id: UUID,
        text: str,
        *,
        follow_up: bool = False,
        is_suggested: bool = False,
    ) -> AskHandle:
        if not can(auth.user, Action.QA_ASK):
            raise Forbidden()
        if self.cfg.qa_off:
            raise AiBusy(reason="disabled")
        conv = await self._own_conversation(auth, conversation_id)
        question = Question.create(
            conv.id, text, follow_up=follow_up and self.cfg.followup_enabled, now=self._clock.now()
        )
        wait = self._rate.acquire(f"q:{auth.user.id}")
        if wait:
            raise RateLimited(retryAfter=seconds(wait))
        docs = await self._docs.ready_documents(self._library_id)  # US-202 AC-202.2: READY only
        if not docs:
            raise NoReadyDocuments()
        processing = await self._docs.processing_count(self._library_id)
        previous = await self._qa.turns(conv.id)
        await self._gate.acquire()  # 503 AI_BUSY before the stream opens
        return AskHandle(self, auth, question, docs, processing, previous, is_suggested)

    async def _pipeline(
        self,
        text: str,
        language: Language,
        docs: dict[UUID, str],
        history: list[Turn],
        cancel: asyncio.Event,
        out: PipelineOutcome,
        t0: float,
    ) -> AsyncIterator[str]:
        """Yields the text to stream (after hold-back); sets `out` to the final decision."""
        query = build_search_query(text, history)
        with span("retrieve", doc_count=len(docs)):
            r0 = time.perf_counter()
            found = await self._retrieval.search(query, list(docs))
            metrics.RETRIEVAL_LATENCY.observe(time.perf_counter() - r0)
        if found.empty:  # ALG-2 → US-304, the LLM is not called (AC-304.4)
            out.status, out.reason = AnswerStatus.NOT_FOUND, NotFoundReason.NO_CHUNKS
            return

        prompt = build_v1(found.chunks, text, language, docs, context_tokens=self.cfg.context_tokens, history=history)
        hold = HoldBack()
        async for piece in self._generate(prompt, cancel, out, t0, hold):
            yield piece
        if out.status is AnswerStatus.FAILED:
            return
        if cancel.is_set():
            out.status, out.text = AnswerStatus.STOPPED, hold.buf
            return
        with span("citations.validate", chunks=len(prompt.chunks)):
            result = citation_policy.validate(hold.buf, prompt.chunks, docs)  # ALG-3 → US-303
        if result.not_found:
            out.status, out.reason = AnswerStatus.NOT_FOUND, result.not_found
            return
        out.status, out.text, out.citations = AnswerStatus.COMPLETED, result.text, result.citations

    async def _generate(
        self, prompt: Prompt, cancel: asyncio.Event, out: PipelineOutcome, t0: float, hold: HoldBack
    ) -> AsyncIterator[str]:
        """Calls the LLM through the circuit breaker; failures end up in `out` (status FAILED + error code)."""
        try:
            self._gate.breaker.before_call()
        except CircuitOpen:
            out.status, out.error_code = AnswerStatus.FAILED, "AI_UNAVAILABLE"
            return
        ok = False
        try:
            with span("llm.stream", chunks=len(prompt.chunks), prompt_tokens=prompt.estimated_tokens()):
                async for piece in self._llm.stream(prompt, cancel, out.stats):
                    if cancel.is_set():
                        break
                    _mark_first_token(out, t0)
                    released = hold.feed(piece)
                    if released:
                        yield released
            ok = True
        except GenerationTimeout:
            out.status, out.error_code = AnswerStatus.FAILED, "AI_TIMEOUT"
        except GenerationUnavailable:
            out.status, out.error_code = AnswerStatus.FAILED, "AI_UNAVAILABLE"
        finally:
            self._record_llm_call(healthy=ok or cancel.is_set(), ok=ok, out=out)

    def _record_llm_call(self, *, healthy: bool, ok: bool, out: PipelineOutcome) -> None:
        # A user pressing "Dừng" is not a provider failure, so it counts as healthy for the breaker.
        self._gate.breaker.record(healthy)
        metrics.LLM_CIRCUIT.set(metrics.CIRCUIT_VALUE[self._gate.breaker.state.value])
        metrics.LLM_REQUESTS.labels("ok" if ok else (out.error_code or "error")).inc()
        metrics.LLM_TOKENS.labels("in").inc(out.stats.input_tokens)
        metrics.LLM_TOKENS.labels("out").inc(out.stats.output_tokens)

    async def stop(self, auth: AuthContext, answer_id: UUID) -> None:
        """US-310. Sets the local flag, or tells the replica that runs the stream (T310.1)."""
        rec = await self._qa.get_answer(answer_id)
        if rec is None or rec.session_id_hash != auth.session_id_hash:
            raise RouteNotFound()
        if rec.status is not AnswerStatus.STREAMING:
            raise InvalidState()
        flag = self._stop_flags.get(answer_id)
        if flag is not None:
            flag.set()
        else:
            await self._bus.publish(answer_id)

    def _on_remote_stop(self, answer_id: UUID) -> None:
        flag = self._stop_flags.get(answer_id)
        if flag is not None:
            flag.set()

    # ------------------------------------------------------------------ feedback (US-309)
    async def feedback(self, auth: AuthContext, answer_id: UUID, value: str, reason: str | None) -> None:
        if value not in FEEDBACK_VALUES or (reason is not None and reason not in FEEDBACK_REASONS):
            raise QuestionInvalid(field="value" if value not in FEEDBACK_VALUES else "reason")
        if value == "HELPFUL":
            reason = None
        rec = await self._qa.get_answer(answer_id)
        if rec is None or rec.session_id_hash != auth.session_id_hash:
            raise RouteNotFound()
        if rec.status is not AnswerStatus.COMPLETED:
            raise InvalidState()
        if not await self._qa.save_feedback(answer_id, value, reason, self._clock.now()):
            raise AlreadySubmitted()
        self._track(auth, "answer_feedback_submitted", {"value": value, "reason": reason})

    # ------------------------------------------------------------------ evaluation (US-402)
    async def answer_for_evaluation(self, text: str) -> tuple[PipelineOutcome, int]:
        """Same pipeline, no conversation, no persistence, no streaming. Returns (outcome, latency_ms)."""
        q = Question.create(uuid7(), text, follow_up=False, now=self._clock.now())
        docs = await self._docs.ready_documents(self._library_id)
        out, t0 = PipelineOutcome(), time.perf_counter()
        if not docs:
            out.status, out.reason = AnswerStatus.NOT_FOUND, NotFoundReason.NO_CHUNKS
            return out, 0
        await self._gate.acquire()
        try:
            async for _ in self._pipeline(q.text, q.language, docs, [], asyncio.Event(), out, t0):
                pass
        finally:
            self._gate.release()
        return out, _ms_since(t0)

    # ------------------------------------------------------------------ helpers
    def _track(self, auth: AuthContext, name: str, props: dict[str, Any]) -> None:
        self._analytics.emit(name, props, user_id=auth.user.id, session_id=auth.session_id_hash.hex()[:16])


def _ms_since(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _mark_first_token(out: PipelineOutcome, t0: float) -> None:
    if out.first_token_ms is None:
        out.first_token_ms = _ms_since(t0)
        metrics.QA_FIRST_TOKEN.observe(out.first_token_ms / 1000)


class HoldBack:
    """§0.5 rule 3: the first HOLD_BACK_CHARS are held until they cannot be the NOT_FOUND token any more."""

    def __init__(self) -> None:
        self.buf, self.released = "", False

    def feed(self, piece: str) -> str | None:
        """Returns the text to emit now (None while holding back)."""
        self.buf += piece
        if self.released:
            return piece
        if len(self.buf) >= HOLD_BACK_CHARS and not citation_policy.could_be_not_found(self.buf):
            self.released = True
            return self.buf
        return None


class AskHandle:
    """One question in flight. `events()` must be consumed exactly once; it always releases the LLM slot."""

    def __init__(
        self,
        svc: QuestionAnsweringService,
        auth: AuthContext,
        question: Question,
        docs: dict[UUID, str],
        processing: int,
        previous: list[Turn],
        is_suggested: bool,
    ) -> None:
        self._svc, self._auth, self.question, self._docs = svc, auth, question, docs
        self._processing, self._previous, self._is_suggested = processing, previous, is_suggested
        self.answer_id = uuid7()

    async def events(self) -> AsyncIterator[SseEvent]:
        svc, q, now = self._svc, self.question, self._svc._clock.now
        t0 = time.perf_counter()
        cancel = asyncio.Event()
        svc._stop_flags[self.answer_id] = cancel
        finished = False
        out = PipelineOutcome()
        try:
            await svc._qa.save_question_and_answer(q, self.answer_id)  # one transaction
            yield "meta", {
                "questionId": str(q.id),
                "answerId": str(self.answer_id),
                "readyDocCount": len(self._docs),
                "processingDocCount": self._processing,
            }
            svc._track(
                self._auth,
                "question_submitted",
                {
                    "language": q.language.value,
                    "question_length": len(q.text),
                    "ready_doc_count": len(self._docs),
                    "is_suggested": self._is_suggested,
                    "turn_index": len(self._previous),
                },
            )
            # US-311: at most the last 2 turns, and only for an explicit follow-up (AC-311.2)
            history = self._previous[-svc.cfg.history_turns :] if q.is_followup else []
            try:
                async for piece in svc._pipeline(q.text, q.language, self._docs, history, cancel, out, t0):
                    yield "delta", {"text": piece}
            except Exception as e:  # noqa: BLE001 — embedder / DB failures end the stream with one error event
                log.error("qa_pipeline_failed", error_type=type(e).__name__, answer_id=str(self.answer_id))
                out.status, out.error_code = AnswerStatus.FAILED, "INTERNAL"

            latency = _ms_since(t0)
            async for ev in self._finish(out, latency, now()):
                yield ev
            finished = True
        finally:
            svc._stop_flags.pop(self.answer_id, None)
            svc._gate.release()
            if not finished:  # client went away mid-stream: stop paying for tokens, record what happened
                cancel.set()
                asyncio.get_running_loop().create_task(
                    _quietly(svc._qa.mark_stopped(self.answer_id, partial_text="", latency_ms=_ms_since(t0), now=now()))
                )

    async def _finish(self, out: PipelineOutcome, latency: int, now: datetime) -> AsyncIterator[SseEvent]:
        svc = self._svc
        status = out.status or AnswerStatus.FAILED
        metrics.QA_LATENCY.labels(status.value).observe(latency / 1000)
        metrics.QA_ANSWERS.labels(status.value, out.reason.value if out.reason else "").inc()
        if status is AnswerStatus.NOT_FOUND and out.reason:
            metrics.QA_NOT_FOUND.labels(out.reason.value).inc()
            if out.reason is NotFoundReason.INVALID_CITATIONS:
                metrics.QA_CITATION_INVALID.inc()
        if status is AnswerStatus.COMPLETED:
            await svc._qa.complete(
                self.answer_id,
                text=out.text,
                citations=out.citations,
                latency_ms=latency,
                first_token_ms=out.first_token_ms,
                model_id=out.stats.model_id,
                now=now,
            )
            svc._track(
                self._auth,
                "answer_completed",
                {
                    "latency_ms": latency,
                    "first_token_ms": out.first_token_ms,
                    "citation_count": len(out.citations),
                    "distinct_docs_cited": len({c.document_id for c in out.citations}),
                    "is_not_found": False,
                    "not_found_reason": None,
                },
            )
            yield "citations", {"text": out.text, "items": [citation_dto(c) for c in out.citations]}
            yield "done", {
                "status": "COMPLETED",
                "reason": None,
                "latencyMs": latency,
                "firstTokenMs": out.first_token_ms,
            }
        elif status is AnswerStatus.NOT_FOUND:
            reason = out.reason or NotFoundReason.MODEL_NOT_FOUND
            await svc._qa.mark_not_found(
                self.answer_id, reason, latency_ms=latency, first_token_ms=out.first_token_ms, now=now
            )
            svc._track(
                self._auth,
                "answer_completed",
                {
                    "latency_ms": latency,
                    "first_token_ms": out.first_token_ms,
                    "citation_count": 0,
                    "distinct_docs_cited": 0,
                    "is_not_found": True,
                    "not_found_reason": reason.value,
                },
            )
            yield "done", {
                "status": "NOT_FOUND",
                "reason": reason.value,
                "latencyMs": latency,
                "firstTokenMs": out.first_token_ms,
            }
        elif status is AnswerStatus.STOPPED:
            await svc._qa.mark_stopped(self.answer_id, partial_text=out.text, latency_ms=latency, now=now)
            svc._track(self._auth, "answer_stopped", {"elapsed_ms": latency})
            yield "done", {
                "status": "STOPPED",
                "reason": None,
                "latencyMs": latency,
                "firstTokenMs": out.first_token_ms,
            }
        else:
            await svc._qa.mark_failed(self.answer_id, latency_ms=latency, now=now)
            code = out.error_code or "INTERNAL"
            error_type = {"AI_TIMEOUT": "timeout", "AI_UNAVAILABLE": "service_error"}.get(code, "service_error")
            svc._track(self._auth, "answer_failed", {"error_type": error_type})
            yield "error", {"code": code, "retryable": True}


def citation_dto(c: Citation) -> dict[str, Any]:
    return {
        "index": c.index,
        "documentId": str(c.document_id),
        "fileName": c.file_name,
        "page": c.page_number,
        "excerpt": c.excerpt,
        "removed": c.removed,
    }


async def _quietly(aw) -> None:
    try:
        await aw
    except Exception:  # noqa: BLE001, S110 — best effort after a client disconnect
        pass
