from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from chatdocs.domain.access.user import Role, User
from chatdocs.domain.documents.document import Document, DocumentStatus, ProcessingErrorCode
from chatdocs.domain.jobs import Job, JobType


@dataclass(frozen=True)
class SessionRecord:
    id_hash: bytes
    user: User
    csrf_secret: bytes
    created_at: datetime
    last_activity_at: datetime


@dataclass(frozen=True)
class DocumentRow:
    document: Document
    uploader_name: str


@dataclass(frozen=True)
class DocumentPage:
    items: list[DocumentRow]
    next_cursor: str | None


class UserRepository(Protocol):
    async def upsert_login(self, *, email: str, display_name: str, role: Role, now: datetime) -> tuple[User, bool]:
        """Create or update the user by e-mail (case-insensitive). Returns (user, created)."""
        ...

    async def get(self, user_id: UUID) -> User | None: ...


class SessionRepository(Protocol):
    async def create(self, *, id_hash: bytes, user_id: UUID, csrf_secret: bytes, now: datetime) -> None: ...

    async def get(self, id_hash: bytes) -> SessionRecord | None: ...

    async def touch(self, id_hash: bytes, now: datetime) -> None: ...

    async def delete(self, id_hash: bytes) -> None: ...

    async def delete_idle(self, before: datetime) -> int: ...


class DocumentRepository(Protocol):
    async def find_active_by_hash(self, library_id: UUID, content_hash: bytes) -> Document | None: ...

    async def create_with_job(self, document: Document, job: Job) -> None:
        """One transaction: insert document + job, then NOTIFY workers (SAD §3.2.2 step 4)."""
        ...

    async def get(self, document_id: UUID) -> Document | None: ...

    async def list(
        self,
        library_id: UUID,
        *,
        name_query: str | None,
        statuses: list[DocumentStatus] | None,
        cursor: str | None,
        limit: int,
    ) -> DocumentPage: ...

    async def mark_processing_with_job(self, document_id: UUID, job: Job) -> None: ...

    async def mark_ready(self, document_id: UUID, page_count: int) -> None: ...

    async def mark_no_text(self, document_id: UUID, page_count: int) -> None: ...

    async def mark_error(self, document_id: UUID, code: ProcessingErrorCode) -> None: ...

    async def ready_documents(self, library_id: UUID) -> dict[UUID, str]:
        """id → file name of every READY, not-removed document. The ONLY source of retrieval filters (RUL-003)."""
        ...

    async def processing_count(self, library_id: UUID) -> int: ...

    async def removed_ids(self, document_ids: list[UUID]) -> set[UUID]: ...

    async def mark_removed_with_job(self, document_id: UUID, removed_by: UUID, now: datetime, job: Job) -> bool:
        """One transaction: tombstone + purge job. False if it was already removed."""
        ...

    async def mark_purged(self, document_id: UUID, now: datetime) -> None: ...

    async def count_purge_overdue(self, before: datetime) -> int: ...


class JobQueue(Protocol):
    async def claim(self, worker_id: str, types: list[JobType], now: datetime) -> Job | None: ...

    async def complete(self, job_id: UUID) -> None: ...

    async def retry_later(self, job_id: UUID, error: str, run_after: datetime) -> None: ...

    async def fail(self, job_id: UUID, error: str) -> None: ...

    async def requeue_stale(self, now: datetime) -> int:
        """Return `running` jobs whose lock is older than their timeout to `queued` (worker restart)."""
        ...

    async def enqueue_once(self, job: Job, slot: str) -> bool:
        """Insert unless a job of the same type with payload.slot == slot exists (scheduled jobs). True if added."""
        ...

    async def enqueue(self, job: Job) -> None: ...


class AuditLog(Protocol):
    async def record(
        self,
        *,
        action: str,
        actor_id: UUID | None,
        target_type: str | None = None,
        target_id: str | None = None,
        ip: str | None = None,
    ) -> None: ...
