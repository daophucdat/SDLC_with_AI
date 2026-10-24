"""Response models — keep in sync with web/src/api-client/types.ts (dev_tasks.md §0.4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from chatdocs.application.document_service import DocumentView


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserRef(CamelModel):
    id: str
    display_name: str


class DocumentDto(CamelModel):
    id: str
    file_name: str
    page_count: int | None
    status: str
    error_code: str | None = None
    uploaded_by: UserRef
    uploaded_at: datetime
    can_remove: bool

    @classmethod
    def of(cls, view: DocumentView) -> DocumentDto:
        d = view.document
        return cls(
            id=str(d.id),
            file_name=d.file_name,
            page_count=d.page_count,
            status=d.status.value,
            error_code=d.error_code.value if d.error_code else None,
            uploaded_by=UserRef(id=str(view.uploader_id), display_name=view.uploader_name),
            uploaded_at=d.uploaded_at,
            can_remove=view.can_remove,
        )


class DocumentListDto(CamelModel):
    items: list[DocumentDto]
    next_cursor: str | None


class MeDto(CamelModel):
    id: str
    display_name: str
    email: str
    role: str
    permissions: list[str]
    flags: list[str]
