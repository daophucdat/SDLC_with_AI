"""PostgreSQL repositories (SQLAlchemy Core, asyncpg). Schema: migrations/versions/0001_init.py."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from chatdocs.domain.access.user import Role, User
from chatdocs.domain.documents.document import Document, DocumentStatus, ProcessingErrorCode
from chatdocs.domain.errors import InvalidState
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import TIMEOUTS, Job, JobStatus, JobType
from chatdocs.ports.repositories import DocumentPage, DocumentRow, SessionRecord


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_size=10, max_overflow=10, pool_pre_ping=True)


async def db_health(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — health probes report, they do not raise
        return False


def _user(row) -> User:
    return User(id=row.user_id, email=row.email, display_name=row.display_name, role=Role(row.role), active=row.active)


# ---------------------------------------------------------------- access
class PgUserRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def upsert_login(self, *, email: str, display_name: str, role: Role, now: datetime) -> tuple[User, bool]:
        sql = text("""
            INSERT INTO access.app_user (id, email, display_name, role, active, created_at, last_login_at)
            VALUES (:id, :email, :name, :role, true, :now, :now)
            ON CONFLICT ((lower(email))) DO UPDATE
               SET display_name = EXCLUDED.display_name, role = EXCLUDED.role, last_login_at = EXCLUDED.last_login_at
            RETURNING id AS user_id, email, display_name, role, active, (xmax = 0) AS created
        """)
        async with self._e.begin() as c:
            row = (
                await c.execute(
                    sql, {"id": uuid7(), "email": email.strip(), "name": display_name, "role": role.value, "now": now}
                )
            ).one()
        return _user(row), bool(row.created)

    async def get(self, user_id: UUID) -> User | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    text("SELECT id AS user_id, email, display_name, role, active FROM access.app_user WHERE id = :id"),
                    {"id": user_id},
                )
            ).first()
        return _user(row) if row else None


class PgSessionRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def create(self, *, id_hash: bytes, user_id: UUID, csrf_secret: bytes, now: datetime) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("""
                INSERT INTO access.session (id_hash, user_id, csrf_secret, created_at, last_activity_at)
                VALUES (:h, :u, :s, :now, :now)"""),
                {"h": id_hash, "u": user_id, "s": csrf_secret, "now": now},
            )

    async def get(self, id_hash: bytes) -> SessionRecord | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    text("""
                SELECT s.id_hash, s.csrf_secret, s.created_at, s.last_activity_at,
                       u.id AS user_id, u.email, u.display_name, u.role, u.active
                  FROM access.session s JOIN access.app_user u ON u.id = s.user_id
                 WHERE s.id_hash = :h"""),
                    {"h": id_hash},
                )
            ).first()
        if not row:
            return None
        return SessionRecord(
            bytes(row.id_hash), _user(row), bytes(row.csrf_secret), row.created_at, row.last_activity_at
        )

    async def touch(self, id_hash: bytes, now: datetime) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("UPDATE access.session SET last_activity_at = :now WHERE id_hash = :h"), {"h": id_hash, "now": now}
            )

    async def delete(self, id_hash: bytes) -> None:
        async with self._e.begin() as c:
            await c.execute(text("DELETE FROM access.session WHERE id_hash = :h"), {"h": id_hash})

    async def delete_idle(self, before: datetime) -> int:
        async with self._e.begin() as c:
            res = await c.execute(text("DELETE FROM access.session WHERE last_activity_at < :b"), {"b": before})
        return res.rowcount or 0


class PgAuditLog:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def record(
        self,
        *,
        action: str,
        actor_id: UUID | None,
        target_type: str | None = None,
        target_id: str | None = None,
        ip: str | None = None,
    ) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("""
                INSERT INTO platform.audit_log (actor_id, action, target_type, target_id, ip)
                VALUES (:a, :act, :tt, :tid, CAST(:ip AS inet))"""),
                {"a": actor_id, "act": action, "tt": target_type, "tid": target_id, "ip": ip},
            )


# ---------------------------------------------------------------- documents
_DOC_COLS = """d.id, d.library_id, d.file_name, d.size_bytes, d.content_hash, d.status, d.storage_key, d.uploaded_by,
               d.uploaded_at, d.page_count, d.error_code, d.removed_at"""


def _doc(row) -> Document:
    return Document(
        id=row.id,
        library_id=row.library_id,
        file_name=row.file_name,
        size_bytes=row.size_bytes,
        content_hash=bytes(row.content_hash),
        status=DocumentStatus(row.status),
        storage_key=row.storage_key,
        uploaded_by=row.uploaded_by,
        uploaded_at=row.uploaded_at,
        page_count=row.page_count,
        error_code=ProcessingErrorCode(row.error_code) if row.error_code else None,
        removed_at=row.removed_at,
    )


def _encode_cursor(ts: datetime, doc_id: UUID) -> str:
    return base64.urlsafe_b64encode(f"{ts.isoformat()}|{doc_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID] | None:
    try:
        ts, did = base64.urlsafe_b64decode(cursor.encode()).decode().split("|", 1)
        return datetime.fromisoformat(ts), UUID(did)
    except (ValueError, UnicodeDecodeError):
        return None


def _like_escape(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_INSERT_JOB = text("""
    INSERT INTO platform.job (id, type, payload, status, attempts, run_after)
    VALUES (:id, :type, CAST(:payload AS jsonb), 'queued', 0, now())""")
_NOTIFY = text("SELECT pg_notify('jobs', :type)")


class PgDocumentRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def find_active_by_hash(self, library_id: UUID, content_hash: bytes) -> Document | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    text(f"""
                SELECT {_DOC_COLS} FROM documents.document d
                 WHERE d.library_id = :lib AND d.content_hash = :h AND d.removed_at IS NULL
                 ORDER BY d.uploaded_at LIMIT 1"""),
                    {"lib": library_id, "h": content_hash},
                )
            ).first()
        return _doc(row) if row else None

    async def create_with_job(self, document: Document, job: Job) -> None:
        d = document
        async with self._e.begin() as c:  # one transaction: no document without its job, and vice versa
            await c.execute(
                text("""
                INSERT INTO documents.document (id, library_id, file_name, size_bytes, content_hash, status,
                                                storage_key, uploaded_by, uploaded_at)
                VALUES (:id, :lib, :name, :size, :hash, :status, :key, :by, :at)"""),
                {
                    "id": d.id,
                    "lib": d.library_id,
                    "name": d.file_name,
                    "size": d.size_bytes,
                    "hash": d.content_hash,
                    "status": d.status.value,
                    "key": d.storage_key,
                    "by": d.uploaded_by,
                    "at": d.uploaded_at,
                },
            )
            await c.execute(_INSERT_JOB, {"id": job.id, "type": job.type.value, "payload": json.dumps(job.payload)})
            await c.execute(_NOTIFY, {"type": job.type.value})  # delivered on commit

    async def get(self, document_id: UUID) -> Document | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    text(f"SELECT {_DOC_COLS} FROM documents.document d WHERE d.id = :id"), {"id": document_id}
                )
            ).first()
        return _doc(row) if row else None

    async def list(
        self,
        library_id: UUID,
        *,
        name_query: str | None,
        statuses: list[DocumentStatus] | None,
        cursor: str | None,
        limit: int,
    ) -> DocumentPage:
        where = ["d.library_id = :lib", "d.removed_at IS NULL"]
        params: dict = {"lib": library_id, "lim": limit + 1}
        if name_query:
            where.append("d.file_name ILIKE :pat ESCAPE '\\'")
            params["pat"] = f"%{_like_escape(name_query)}%"
        if statuses:
            where.append("d.status = ANY(:statuses)")
            params["statuses"] = [s.value for s in statuses]
        if cursor and (decoded := _decode_cursor(cursor)):
            where.append("(d.uploaded_at, d.id) < (:cts, :cid)")
            params["cts"], params["cid"] = decoded
        sql = text(f"""
            SELECT {_DOC_COLS}, u.display_name AS uploader_name
              FROM documents.document d JOIN access.app_user u ON u.id = d.uploaded_by
             WHERE {' AND '.join(where)}
             ORDER BY d.uploaded_at DESC, d.id DESC
             LIMIT :lim""")
        async with self._e.connect() as c:
            rows = (await c.execute(sql, params)).all()
        items = [DocumentRow(_doc(r), r.uploader_name) for r in rows[:limit]]
        nxt = _encode_cursor(items[-1].document.uploaded_at, items[-1].document.id) if len(rows) > limit else None
        return DocumentPage(items, nxt)

    async def mark_processing_with_job(self, document_id: UUID, job: Job) -> None:
        async with self._e.begin() as c:
            res = await c.execute(
                text("""
                UPDATE documents.document SET status = 'PROCESSING', error_code = NULL
                 WHERE id = :id AND status = 'ERROR' AND removed_at IS NULL"""),
                {"id": document_id},
            )
            if res.rowcount != 1:
                raise InvalidState("document is no longer in ERROR state")
            await c.execute(_INSERT_JOB, {"id": job.id, "type": job.type.value, "payload": json.dumps(job.payload)})
            await c.execute(_NOTIFY, {"type": job.type.value})

    async def _set_status(self, document_id: UUID, status: str, page_count: int | None, code: str | None) -> None:
        # Only a PROCESSING document moves on: a document removed meanwhile is never "resurrected".
        async with self._e.begin() as c:
            await c.execute(
                text("""
                UPDATE documents.document SET status = :st, page_count = COALESCE(:pc, page_count), error_code = :code
                 WHERE id = :id AND status = 'PROCESSING'"""),
                {"id": document_id, "st": status, "pc": page_count, "code": code},
            )

    async def mark_ready(self, document_id: UUID, page_count: int) -> None:
        await self._set_status(document_id, "READY", page_count, None)

    async def mark_no_text(self, document_id: UUID, page_count: int) -> None:
        await self._set_status(document_id, "NO_TEXT", page_count, None)

    async def mark_error(self, document_id: UUID, code: ProcessingErrorCode) -> None:
        await self._set_status(document_id, "ERROR", None, code.value)

    async def ready_documents(self, library_id: UUID) -> dict[UUID, str]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text("""
                SELECT id, file_name FROM documents.document
                 WHERE library_id = :lib AND status = 'READY' AND removed_at IS NULL"""),
                    {"lib": library_id},
                )
            ).all()
        return {r.id: r.file_name for r in rows}

    async def processing_count(self, library_id: UUID) -> int:
        async with self._e.connect() as c:
            return (
                await c.execute(
                    text("""
                SELECT count(*) FROM documents.document
                 WHERE library_id = :lib AND status IN ('UPLOADING', 'PROCESSING') AND removed_at IS NULL"""),
                    {"lib": library_id},
                )
            ).scalar_one()

    async def removed_ids(self, document_ids: list[UUID]) -> set[UUID]:
        if not document_ids:
            return set()
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text("SELECT id FROM documents.document WHERE id = ANY(:ids) AND removed_at IS NOT NULL"),
                    {"ids": list(document_ids)},
                )
            ).all()
        return {r.id for r in rows}

    async def mark_removed_with_job(self, document_id: UUID, removed_by: UUID, now: datetime, job: Job) -> bool:
        async with self._e.begin() as c:  # tombstone + purge job in one transaction (T204.1)
            res = await c.execute(
                text("""
                UPDATE documents.document SET status = 'REMOVED', removed_at = :now, removed_by = :by
                 WHERE id = :id AND removed_at IS NULL"""),
                {"id": document_id, "now": now, "by": removed_by},
            )
            if res.rowcount != 1:
                return False
            await c.execute(_INSERT_JOB, {"id": job.id, "type": job.type.value, "payload": json.dumps(job.payload)})
            await c.execute(_NOTIFY, {"type": job.type.value})
        return True

    async def mark_purged(self, document_id: UUID, now: datetime) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("UPDATE documents.document SET purged_at = :now WHERE id = :id"), {"id": document_id, "now": now}
            )

    async def count_purge_overdue(self, before: datetime) -> int:
        async with self._e.connect() as c:
            return (
                await c.execute(
                    text("""
                SELECT count(*) FROM documents.document
                 WHERE removed_at IS NOT NULL AND purged_at IS NULL AND removed_at < :b"""),
                    {"b": before},
                )
            ).scalar_one()


# ---------------------------------------------------------------- jobs
def _job(row) -> Job:
    payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
    return Job(
        id=row.id,
        type=JobType(row.type),
        payload=payload,
        status=JobStatus(row.status),
        attempts=row.attempts,
        run_after=row.run_after,
    )


class PgJobQueue:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def claim(self, worker_id: str, types: list[JobType], now: datetime) -> Job | None:
        sql = text("""
            UPDATE platform.job SET status = 'running', locked_by = :w, locked_at = :now, attempts = attempts + 1
             WHERE id = (SELECT id FROM platform.job
                          WHERE status = 'queued' AND run_after <= :now AND type = ANY(:types)
                          ORDER BY run_after FOR UPDATE SKIP LOCKED LIMIT 1)
            RETURNING id, type, payload, status, attempts, run_after""")
        async with self._e.begin() as c:
            row = (await c.execute(sql, {"w": worker_id, "now": now, "types": [t.value for t in types]})).first()
        return _job(row) if row else None

    async def complete(self, job_id: UUID) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("UPDATE platform.job SET status = 'done', locked_by = NULL WHERE id = :id"), {"id": job_id}
            )

    async def retry_later(self, job_id: UUID, error: str, run_after: datetime) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("""
                UPDATE platform.job SET status = 'queued', run_after = :ra, last_error = :err,
                                        locked_by = NULL, locked_at = NULL
                 WHERE id = :id"""),
                {"id": job_id, "ra": run_after, "err": error[:500]},
            )

    async def fail(self, job_id: UUID, error: str) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("""
                UPDATE platform.job SET status = 'failed', last_error = :err, locked_by = NULL WHERE id = :id"""),
                {"id": job_id, "err": error[:500]},
            )

    async def enqueue(self, job: Job) -> None:
        async with self._e.begin() as c:
            await c.execute(_INSERT_JOB, {"id": job.id, "type": job.type.value, "payload": json.dumps(job.payload)})
            await c.execute(_NOTIFY, {"type": job.type.value})

    async def enqueue_once(self, job: Job, slot: str) -> bool:
        # ux_job_slot (migration 0002) makes this safe with several workers scheduling at the same time.
        async with self._e.begin() as c:
            res = await c.execute(
                text("""
                INSERT INTO platform.job (id, type, payload, status, attempts, run_after)
                VALUES (:id, :type, CAST(:payload AS jsonb), 'queued', 0, now())
                ON CONFLICT DO NOTHING"""),
                {"id": job.id, "type": job.type.value, "payload": json.dumps({**job.payload, "slot": slot})},
            )
            if res.rowcount:
                await c.execute(_NOTIFY, {"type": job.type.value})
        return bool(res.rowcount)

    async def queued_stats(self) -> dict[str, tuple[int, float]]:
        """type → (queued count, age in seconds of the oldest ready job) for the queue alerts (SAD §4.3)."""
        async with self._e.connect() as c:
            rows = (await c.execute(text("""
                SELECT type, count(*) AS n,
                       COALESCE(EXTRACT(EPOCH FROM now() - min(run_after) FILTER (WHERE run_after <= now())), 0)
                         AS oldest
                  FROM platform.job WHERE status = 'queued' GROUP BY type"""))).all()
        return {r.type: (int(r.n), float(r.oldest)) for r in rows}

    async def requeue_stale(self, now: datetime) -> int:
        total = 0
        async with self._e.begin() as c:
            for job_type, timeout in TIMEOUTS.items():
                res = await c.execute(
                    text("""
                    UPDATE platform.job SET status = 'queued', locked_by = NULL, locked_at = NULL
                     WHERE status = 'running' AND type = :t AND locked_at < :limit"""),
                    {"t": job_type.value, "limit": now - timeout - timedelta(minutes=1)},
                )
                total += res.rowcount or 0
        return total
