"""Document lifecycle (SAD §3.1 state diagram)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from uuid import UUID

from chatdocs.domain.errors import InvalidState


class DocumentStatus(str, Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    NO_TEXT = "NO_TEXT"
    ERROR = "ERROR"
    REMOVED = "REMOVED"


class ProcessingErrorCode(str, Enum):
    PASSWORD = "PASSWORD"  # noqa: S105 — error code, not a secret
    CORRUPT = "CORRUPT"
    NOT_PDF = "NOT_PDF"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class Document:
    id: UUID
    library_id: UUID
    file_name: str
    size_bytes: int
    content_hash: bytes
    status: DocumentStatus
    storage_key: str
    uploaded_by: UUID
    uploaded_at: datetime
    page_count: int | None = None
    error_code: ProcessingErrorCode | None = None
    removed_at: datetime | None = None

    @staticmethod
    def storage_key_for(library_id: UUID, document_id: UUID) -> str:
        return f"library/{library_id}/doc/{document_id}.pdf"

    def is_queryable(self) -> bool:
        return self.status is DocumentStatus.READY and self.removed_at is None

    def retried(self) -> Document:
        if self.status is not DocumentStatus.ERROR:
            raise InvalidState(f"cannot retry a document in state {self.status.value}")
        return replace(self, status=DocumentStatus.PROCESSING, error_code=None)
