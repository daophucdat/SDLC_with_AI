"""DocumentService — US-201 (upload), US-202 (status, retry), US-204 (remove + purge), US-205, US-206 (duplicate
warning), US-305 (serve the original PDF by byte range)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from chatdocs.domain.access.permissions import Action, can
from chatdocs.domain.access.user import Role, User
from chatdocs.domain.documents.document import Document, DocumentStatus
from chatdocs.domain.documents.upload_policy import UploadPolicy
from chatdocs.domain.errors import DocumentNotFound, DuplicateDocument, Forbidden, RateLimited
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import Job, JobType
from chatdocs.platform.rate_limit import RateLimiter, seconds
from chatdocs.ports.chunk_index import ChunkIndex
from chatdocs.ports.clock import Clock
from chatdocs.ports.qa import AnalyticsSink
from chatdocs.ports.repositories import AuditLog, DocumentRepository
from chatdocs.ports.storage import DocumentStorage

PURGE_ALERT_AFTER = timedelta(hours=20)  # SEC-06: purge must finish within 24 h; alert with 4 h margin


@dataclass(frozen=True)
class ReceivedFile:
    """What the HTTP adapter hands over after streaming the upload to a temp file."""

    file_name: str
    local_path: str
    size_bytes: int
    sha256: bytes
    head: bytes  # first bytes, for the %PDF- check


@dataclass(frozen=True)
class DocumentView:
    document: Document
    uploader_id: UUID
    uploader_name: str
    can_remove: bool


@dataclass(frozen=True)
class DocumentList:
    items: list[DocumentView]
    next_cursor: str | None


@dataclass(frozen=True)
class FileSlice:
    """Bytes [start, end] of a `total`-byte PDF; `partial` = the request had a Range header (→ 206)."""

    file_name: str
    start: int
    end: int
    total: int
    partial: bool
    body: AsyncIterator[bytes]


class RangeNotSatisfiable(Exception):
    def __init__(self, total: int) -> None:
        self.total = total


def parse_range(header: str | None, total: int) -> tuple[int, int] | None:
    """Single `bytes=a-b` / `bytes=a-` / `bytes=-n` range; None means the whole file. Raises on unsatisfiable."""
    if not header:
        return None
    unit, _, spec = header.partition("=")
    if unit.strip().lower() != "bytes" or "," in spec:
        return None  # unsupported forms → serve the whole file (allowed by RFC 9110)
    first, _, last = spec.strip().partition("-")
    try:
        if first == "":
            n = int(last)
            start, end = max(0, total - n), total - 1
        else:
            start = int(first)
            end = min(int(last), total - 1) if last else total - 1
    except ValueError:
        return None
    if start >= total or start > end:
        raise RangeNotSatisfiable(total)
    return start, end


class DocumentService:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        storage: DocumentStorage,
        audit: AuditLog,
        policy: UploadPolicy,
        library_id: UUID,
        clock: Clock,
        analytics: AnalyticsSink | None = None,
        upload_limiter: RateLimiter | None = None,
        index: ChunkIndex | None = None,  # only the worker purges, so only it passes the index
    ) -> None:
        self._docs, self._storage, self._audit = documents, storage, audit
        self._policy, self._library_id, self._clock = policy, library_id, clock
        self._analytics, self._upload_limiter, self._index = analytics, upload_limiter, index

    async def upload(self, user: User, file: ReceivedFile, *, force: bool, ip: str | None) -> Document:
        if not can(user, Action.DOCUMENTS_UPLOAD):
            raise Forbidden()
        if self._upload_limiter and (wait := self._upload_limiter.acquire(f"up:{user.id}")):
            raise RateLimited(retryAfter=seconds(wait))
        self._policy.check_size(file.size_bytes)
        self._policy.check_head(file.head)
        name = self._policy.clean_file_name(file.file_name)

        if not force:
            existing = await self._docs.find_active_by_hash(self._library_id, file.sha256)
            if existing is not None:
                raise DuplicateDocument(existingId=str(existing.id), uploadedAt=_iso(existing.uploaded_at))

        doc_id = uuid7()
        doc = Document(
            id=doc_id,
            library_id=self._library_id,
            file_name=name,
            size_bytes=file.size_bytes,
            content_hash=file.sha256,
            status=DocumentStatus.PROCESSING,
            storage_key=Document.storage_key_for(self._library_id, doc_id),
            uploaded_by=user.id,
            uploaded_at=self._clock.now(),
        )
        # Object first, then the DB transaction. A failure in between leaves an orphan object
        # (cleaned daily), never a document row pointing at nothing.
        await self._storage.put_file(doc.storage_key, file.local_path, file.size_bytes)
        await self._docs.create_with_job(
            doc, Job(id=uuid7(), type=JobType.PROCESS_DOCUMENT, payload={"document_id": str(doc_id)})
        )
        await self._audit.record(
            action="upload", actor_id=user.id, target_type="document", target_id=str(doc_id), ip=ip
        )
        return doc

    async def list(
        self,
        user: User,
        *,
        name_query: str | None,
        statuses: list[DocumentStatus] | None,
        cursor: str | None,
        limit: int,
    ) -> DocumentList:
        if not can(user, Action.DOCUMENTS_READ):
            raise Forbidden()
        q = (name_query or "").strip()
        page = await self._docs.list(
            self._library_id,
            name_query=q if len(q) >= 2 else None,
            statuses=statuses,
            cursor=cursor,
            limit=max(1, min(limit, 100)),
        )
        return DocumentList(
            items=[
                DocumentView(
                    r.document,
                    r.document.uploaded_by,
                    r.uploader_name,
                    can(user, Action.DOCUMENTS_REMOVE, r.document.uploaded_by),
                )
                for r in page.items
            ],
            next_cursor=page.next_cursor,
        )

    async def retry(self, user: User, document_id: UUID) -> Document:
        doc = await self._docs.get(document_id)
        if doc is None or doc.removed_at is not None:
            raise DocumentNotFound()
        if not can(user, Action.DOCUMENTS_REMOVE, doc.uploaded_by):  # same rule as removing: uploader or lead
            raise Forbidden()
        retried = doc.retried()  # raises InvalidState unless ERROR
        await self._docs.mark_processing_with_job(
            doc.id, Job(id=uuid7(), type=JobType.PROCESS_DOCUMENT, payload={"document_id": str(doc.id)})
        )
        return retried

    # ------------------------------------------------------------------ US-204
    async def remove(self, user: User, document_id: UUID, *, ip: str | None) -> Document:
        doc = await self._docs.get(document_id)
        if doc is None or doc.removed_at is not None:
            raise DocumentNotFound()
        if not can(user, Action.DOCUMENTS_REMOVE, doc.uploaded_by):
            raise Forbidden()  # AC-204.5
        now = self._clock.now()
        job = Job(id=uuid7(), type=JobType.PURGE_DOCUMENT, payload={"document_id": str(doc.id)})
        if not await self._docs.mark_removed_with_job(doc.id, user.id, now, job):
            raise DocumentNotFound()  # removed concurrently
        await self._audit.record(
            action="remove", actor_id=user.id, target_type="document", target_id=str(doc.id), ip=ip
        )
        if self._analytics:
            role = "uploader" if doc.uploaded_by == user.id else ("lead" if user.role is Role.BD_LEAD else "uploader")
            self._analytics.emit(
                "document_removed",
                {"role": role, "doc_age_days": max(0, (now - doc.uploaded_at).days)},
                user_id=user.id,
                session_id=None,
            )
        return doc

    async def purge(self, document_id: UUID) -> None:
        """Job purge_document (T204.2): object + chunks + pages go; the row stays as a tombstone."""
        doc = await self._docs.get(document_id)
        if doc is None or doc.removed_at is None:
            return
        await self._storage.delete(doc.storage_key)
        if self._index is not None:
            await self._index.replace_document(doc.id, [], [], [])
        await self._docs.mark_purged(doc.id, self._clock.now())

    async def purge_overdue(self) -> int:
        return await self._docs.count_purge_overdue(self._clock.now() - PURGE_ALERT_AFTER)

    # ------------------------------------------------------------------ US-305
    async def open_file(self, user: User, document_id: UUID, range_header: str | None) -> FileSlice:
        if not can(user, Action.DOCUMENTS_READ):
            raise Forbidden()
        doc = await self._docs.get(document_id)
        if doc is None or doc.removed_at is not None:
            raise DocumentNotFound()  # EC-16: also after removal
        total = await self._storage.size(doc.storage_key)
        if total is None:
            raise DocumentNotFound()
        rng = parse_range(range_header, total)
        start, end = rng if rng else (0, total - 1)
        return FileSlice(
            doc.file_name, start, end, total, rng is not None, self._storage.read_range(doc.storage_key, start, end)
        )


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")
