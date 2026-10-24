"""Integration tests (real PostgreSQL + pgvector, CI) for the Sprint 2 → 4 repositories and migration 0002.

Same database and fixtures as test_postgres.py (TEST_DATABASE_URL)."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from chatdocs.application.analytics_service import EventRecord
from chatdocs.domain.evaluation.test_set import TestCase
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import Job, JobType
from chatdocs.domain.qa.citation_policy import Citation
from chatdocs.domain.qa.question import AnswerStatus, NotFoundReason, Question
from chatdocs.platform.config import DEFAULT_LIBRARY_ID
from chatdocs.ports.insights import EvaluationResult
from chatdocs.ports.qa import Conversation
from tests.integration.test_postgres import NOW, URL, _doc, _user

pytestmark = [pytest.mark.integration, pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")]


async def _session(engine, user_id) -> bytes:
    from chatdocs.adapters.db.repositories import PgSessionRepository

    h = uuid7().bytes + uuid7().bytes
    await PgSessionRepository(engine).create(id_hash=h, user_id=user_id, csrf_secret=b"s" * 32, now=NOW)
    return h


async def test_qa_roundtrip_cascade_and_feedback(engine):
    from chatdocs.adapters.db.qa_repository import PgQaRepository
    from chatdocs.adapters.db.repositories import PgDocumentRepository, PgSessionRepository

    user, _ = await _user(engine)
    sess = await _session(engine, user.id)
    docs = PgDocumentRepository(engine)
    doc = _doc(user.id)
    await docs.create_with_job(doc, Job(id=uuid7(), type=JobType.PROCESS_DOCUMENT, payload={}))
    repo = PgQaRepository(engine)
    conv = Conversation(uuid7(), sess, user.id)
    await repo.create_conversation(conv, NOW)
    assert await repo.get_conversation(conv.id) == conv

    q = Question.create(conv.id, "Điều khoản thanh toán?", follow_up=False, now=NOW)
    a = uuid7()
    await repo.save_question_and_answer(q, a)
    assert (await repo.get_answer(a)).status is AnswerStatus.STREAMING
    cite = Citation(1, None, doc.id, doc.file_name, 3, "Thanh toán 30%")
    await repo.complete(
        a, text="Thanh toán 30% [1]", citations=[cite], latency_ms=900, first_token_ms=300, model_id="m", now=NOW
    )
    await repo.mark_failed(a, latency_ms=1, now=NOW)  # no effect: only STREAMING answers move
    turns = await repo.turns(conv.id)
    assert turns[0].status is AnswerStatus.COMPLETED and turns[0].citations[0].page_number == 3
    assert not turns[0].citations[0].removed

    assert await repo.save_feedback(a, "HELPFUL", None, NOW) is True
    assert await repo.save_feedback(a, "NOT_HELPFUL", "wrong", NOW) is False

    q2 = Question.create(conv.id, "Câu khác?", follow_up=True, now=NOW + timedelta(seconds=1))
    a2 = uuid7()
    await repo.save_question_and_answer(q2, a2)
    await repo.mark_not_found(a2, NotFoundReason.NO_CHUNKS, latency_ms=50, first_token_ms=None, now=NOW)
    assert [t.status for t in await repo.turns(conv.id, limit=1)] == [AnswerStatus.NOT_FOUND]

    # removing the document marks old citations (EC-15)
    await docs.mark_removed_with_job(doc.id, user.id, NOW, Job(id=uuid7(), type=JobType.PURGE_DOCUMENT, payload={}))
    assert (await repo.turns(conv.id))[0].citations[0].removed

    # PD-04: deleting the session deletes the conversation and everything in it
    await PgSessionRepository(engine).delete(sess)
    assert await repo.get_conversation(conv.id) is None
    assert await repo.get_answer(a) is None


async def test_ready_documents_removal_purge_and_overdue(engine):
    from chatdocs.adapters.db.repositories import PgDocumentRepository

    user, _ = await _user(engine)
    docs = PgDocumentRepository(engine)
    d1, d2 = _doc(user.id, "a.pdf", b"h1"), _doc(user.id, "b.pdf", b"h2")
    for d in (d1, d2):
        await docs.create_with_job(d, Job(id=uuid7(), type=JobType.PROCESS_DOCUMENT, payload={}))
    await docs.mark_ready(d1.id, 3)
    assert await docs.ready_documents(DEFAULT_LIBRARY_ID) == {d1.id: "a.pdf"}
    assert await docs.processing_count(DEFAULT_LIBRARY_ID) == 1

    purge = Job(id=uuid7(), type=JobType.PURGE_DOCUMENT, payload={"document_id": str(d1.id)})
    assert await docs.mark_removed_with_job(d1.id, user.id, NOW, purge) is True
    assert await docs.mark_removed_with_job(d1.id, user.id, NOW, purge) is False
    assert await docs.ready_documents(DEFAULT_LIBRARY_ID) == {}  # RUL-003
    assert await docs.removed_ids([d1.id, d2.id]) == {d1.id}
    assert await docs.count_purge_overdue(NOW + timedelta(hours=1)) == 1
    await docs.mark_purged(d1.id, NOW)
    assert await docs.count_purge_overdue(NOW + timedelta(hours=1)) == 0
    assert (await docs.get(d1.id)).removed_at is not None  # tombstone kept


async def test_enqueue_once_dedupes_scheduled_slots(engine):
    from chatdocs.adapters.db.repositories import PgJobQueue

    q = PgJobQueue(engine)
    results = await asyncio.gather(
        *(q.enqueue_once(Job(id=uuid7(), type=JobType.SWEEP_SESSIONS, payload={}), "sweep:1") for _ in range(5))
    )
    assert sorted(results) == [False, False, False, False, True]
    assert await q.enqueue_once(Job(id=uuid7(), type=JobType.SWEEP_SESSIONS, payload={}), "sweep:2")
    assert (await q.queued_stats())["sweep_sessions"][0] == 2


async def test_analytics_writer_rollup_and_weekly(engine):
    from chatdocs.adapters.analytics.postgres_sink import PostgresEventWriter
    from chatdocs.adapters.db.insights_repository import PgMetricsRepository

    async with engine.begin() as c:
        await c.execute(text("TRUNCATE analytics.event, analytics.daily_rollup"))
    w = PostgresEventWriter(engine, flush_seconds=0.05)
    await w.start()
    day = NOW
    for i, (name, props) in enumerate(
        [
            ("question_submitted", {"language": "vi"}),
            ("question_submitted", {"language": "vi"}),
            ("answer_completed", {"latency_ms": 1000, "is_not_found": False}),
            ("answer_completed", {"latency_ms": 9000, "is_not_found": False}),
            ("answer_completed", {"latency_ms": 10, "is_not_found": True}),
            ("answer_feedback_submitted", {"value": "HELPFUL"}),
        ]
    ):
        w.submit(EventRecord(name, day, f"user{i % 2}", None, "0.1.0", props))
    await w.close()

    repo = PgMetricsRepository(engine)
    values = await repo.compute_day(day.date())
    assert values["questions"] == 2 and values["active_users"] == 2 and values["not_found"] == 1
    assert values["helpful"] == 1 and 8500 <= values["p95_latency_ms"] <= 9000
    await repo.save_day(day.date(), values)
    await repo.save_day(day.date(), values)  # idempotent
    monday = day.date() - timedelta(days=day.weekday())
    assert (await repo.daily(monday))[day.date()]["questions"] == 2
    assert (await repo.weekly_active_users(monday)) == {monday: 2}


async def test_partitions_are_created_ahead(engine):
    from chatdocs.adapters.db.insights_repository import PgMetricsRepository

    actions = await PgMetricsRepository(engine).ensure_partitions(date(2026, 11, 9), months_ahead=2, keep_months=13)
    async with engine.connect() as c:
        for name in ("event_202612", "event_202701"):
            assert (await c.execute(text("SELECT to_regclass(:n) IS NOT NULL"), {"n": f"analytics.{name}"})).scalar()
    again = await PgMetricsRepository(engine).ensure_partitions(date(2026, 11, 9), 2, 13)
    assert len(again) <= len(actions)


async def test_evaluation_repository(engine):
    from chatdocs.adapters.db.insights_repository import PgEvaluationRepository

    user, _ = await _user(engine)
    repo = PgEvaluationRepository(engine)
    run = uuid7()
    await repo.create_run(
        run, "bo.xlsx", [TestCase(1, "Giá?", "1 tỷ", False), TestCase(2, "Màu?", None, True)], user.id
    )
    st = await repo.get_run(run)
    assert (st.status, st.done, st.total) == ("queued", 0, 2)
    (cid, case), _ = await repo.cases(run)
    await repo.save_result(run, cid, EvaluationResult(case, "1 tỷ [1]", "COMPLETED", [{"index": 1}], 800))
    await repo.save_result(run, cid, EvaluationResult(case, "dup", "COMPLETED", [], 1))  # ignored
    await repo.set_status(run, "done", NOW)
    assert await repo.done_case_ids(run) == {cid}
    res = await repo.results(run)
    assert [r.status for r in res] == ["COMPLETED", "NOT_RUN"] and res[0].citations == [{"index": 1}]


async def test_stop_bus_crosses_connections(engine):
    from chatdocs.adapters.db.qa_repository import PgStopBus

    listener, sender = PgStopBus(engine), PgStopBus(engine)
    got = asyncio.Event()
    target = uuid7()
    listener.subscribe(lambda aid: got.set() if aid == target else None)
    await listener.start()
    await sender.publish(target)
    await asyncio.wait_for(got.wait(), 5)
    await listener.close()
