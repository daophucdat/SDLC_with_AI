"""Integration tests against a real PostgreSQL 16 + pgvector (CI service container).

Run locally: TEST_DATABASE_URL=postgresql+asyncpg://chatdocs:chatdocs@localhost:5432/chatdocs_test pytest -m integration
The database is recreated from migration 0001 for the test session."""

from __future__ import annotations

import asyncio
import math
import os
from datetime import datetime, timedelta, timezone

import pytest

from chatdocs.domain.access.user import Role
from chatdocs.domain.documents.chunking import chunk_document
from chatdocs.domain.documents.document import Document, DocumentStatus
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import Job, JobStatus, JobType
from chatdocs.platform.config import DEFAULT_LIBRARY_ID

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [pytest.mark.integration, pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")]
NOW = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def migrated():
    from alembic import command
    from alembic.config import Config

    root = os.path.join(os.path.dirname(__file__), "..", "..")
    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", URL)
    command.downgrade(cfg, "base")  # no-op on a fresh database; drops the schemas left by a previous run
    command.upgrade(cfg, "head")
    return URL


@pytest.fixture
async def engine(migrated):
    from sqlalchemy import text

    from chatdocs.adapters.db.repositories import make_engine

    e = make_engine(migrated)
    async with e.begin() as c:
        await c.execute(
            text(
                "TRUNCATE platform.job, qa.conversation, documents.document, access.session, " "access.app_user CASCADE"
            )
        )
    yield e
    await e.dispose()


def vec(seed: int, dim: int = 1024) -> list[float]:
    v = [math.sin(seed * (i + 1)) for i in range(dim)]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


async def _user(engine):
    from chatdocs.adapters.db.repositories import PgUserRepository

    return await PgUserRepository(engine).upsert_login(
        email="Thu.Ha@congty.vn", display_name="Trần Thu Hà", role=Role.BD_MEMBER, now=NOW
    )


async def test_user_upsert_is_case_insensitive_and_reports_created(engine):
    from chatdocs.adapters.db.repositories import PgUserRepository

    repo = PgUserRepository(engine)
    u1, created1 = await _user(engine)
    u2, created2 = await repo.upsert_login(email="thu.ha@CONGTY.vn", display_name="Hà", role=Role.BD_LEAD, now=NOW)
    assert created1 and not created2 and u1.id == u2.id and u2.role is Role.BD_LEAD


async def test_session_roundtrip_and_audit_default_partition(engine):
    from chatdocs.adapters.db.repositories import PgAuditLog, PgSessionRepository

    user, _ = await _user(engine)
    sessions = PgSessionRepository(engine)
    await sessions.create(id_hash=b"h" * 32, user_id=user.id, csrf_secret=b"s" * 32, now=NOW)
    rec = await sessions.get(b"h" * 32)
    assert rec.user.email == user.email and rec.csrf_secret == b"s" * 32
    assert await sessions.delete_idle(NOW + timedelta(hours=9)) == 1
    await PgAuditLog(engine).record(action="login", actor_id=user.id, ip="10.0.0.1")  # needs the DEFAULT partition


def _doc(user_id, name="a.pdf", h=b"hash") -> Document:
    did = uuid7()
    return Document(
        did,
        DEFAULT_LIBRARY_ID,
        name,
        100,
        h,
        DocumentStatus.PROCESSING,
        Document.storage_key_for(DEFAULT_LIBRARY_ID, did),
        user_id,
        NOW,
    )


async def test_document_with_job_and_skip_locked_claim(engine):
    from chatdocs.adapters.db.repositories import PgDocumentRepository, PgJobQueue

    user, _ = await _user(engine)
    docs, queue = PgDocumentRepository(engine), PgJobQueue(engine)
    for i in range(3):
        d = _doc(user.id, f"d{i}.pdf", h=f"h{i}".encode())
        await docs.create_with_job(d, Job(uuid7(), JobType.PROCESS_DOCUMENT, {"document_id": str(d.id)}))
    assert (await docs.find_active_by_hash(DEFAULT_LIBRARY_ID, b"h1")).file_name == "d1.pdf"

    claimed = await asyncio.gather(
        *(queue.claim(f"w{i}", [JobType.PROCESS_DOCUMENT], NOW + timedelta(seconds=5)) for i in range(5))
    )
    got = [j for j in claimed if j]
    assert len(got) == 3 and len({j.id for j in got}) == 3  # SKIP LOCKED: no job is handed out twice
    assert all(j.status is JobStatus.RUNNING and j.attempts == 1 for j in got)
    await queue.retry_later(got[0].id, "boom", NOW + timedelta(minutes=1))
    assert await queue.claim("w", [JobType.PROCESS_DOCUMENT], NOW + timedelta(seconds=10)) is None
    assert (await queue.claim("w", [JobType.PROCESS_DOCUMENT], NOW + timedelta(minutes=2))).attempts == 2


async def test_document_list_filters_and_status_transitions(engine):
    from chatdocs.adapters.db.repositories import PgDocumentRepository

    user, _ = await _user(engine)
    docs = PgDocumentRepository(engine)
    a, b = _doc(user.id, "Hop_dong_100%_X.pdf", b"a"), _doc(user.id, "Bao_gia.pdf", b"b")
    for d in (a, b):
        await docs.create_with_job(d, Job(uuid7(), JobType.PROCESS_DOCUMENT, {"document_id": str(d.id)}))
    await docs.mark_ready(a.id, 3)
    page = await docs.list(DEFAULT_LIBRARY_ID, name_query="100%", statuses=None, cursor=None, limit=10)
    assert [r.document.file_name for r in page.items] == ["Hop_dong_100%_X.pdf"]  # % is escaped, not a wildcard
    page = await docs.list(DEFAULT_LIBRARY_ID, name_query=None, statuses=[DocumentStatus.READY], cursor=None, limit=10)
    assert [r.document.page_count for r in page.items] == [3]
    page = await docs.list(DEFAULT_LIBRARY_ID, name_query=None, statuses=None, cursor=None, limit=1)
    nxt = await docs.list(DEFAULT_LIBRARY_ID, name_query=None, statuses=None, cursor=page.next_cursor, limit=1)
    assert page.next_cursor and len(nxt.items) == 1 and nxt.items[0].document.id != page.items[0].document.id
    await docs.mark_no_text(a.id, 9)  # READY is not PROCESSING any more: no change
    assert (await docs.get(a.id)).status is DocumentStatus.READY


async def test_chunk_index_vector_and_vietnamese_fulltext(engine):
    from chatdocs.adapters.db.repositories import PgDocumentRepository
    from chatdocs.adapters.pgvector.chunk_index import PgVectorChunkIndex

    user, _ = await _user(engine)
    d = _doc(user.id)
    await PgDocumentRepository(engine).create_with_job(d, Job(uuid7(), JobType.PROCESS_DOCUMENT, {}))
    pages = ["Điều 3. Thanh toán 30% giá trị hợp đồng trong vòng 07 ngày.", "Bảo hành 12 tháng."]
    chunks = chunk_document(pages, 500, 80)
    index = PgVectorChunkIndex(engine)
    await index.replace_document(d.id, pages, chunks, [vec(i + 1) for i in range(len(chunks))])
    await index.replace_document(d.id, pages, chunks, [vec(i + 1) for i in range(len(chunks))])  # idempotent

    hits = await index.vector_search(vec(2), [d.id], k=5)
    assert len(hits) == 2 and hits[0].page_number == 2 and hits[0].cosine > 0.99
    fts = await index.fts_search("thanh toan hop dong", [d.id], k=5)  # no diacritics in the query
    assert fts and fts[0].page_number == 1
    assert await index.vector_search(vec(2), [uuid7()], k=5) == []  # never outside the given documents
