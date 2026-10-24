"""/api/v1 — every route here requires a session (router-level dependency = default deny, T102.3)."""

from __future__ import annotations

import hashlib
import os
import tempfile
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from chatdocs.adapters.http.auth import client_ip, container_of, current_auth, current_user
from chatdocs.adapters.http.schemas import DocumentDto, DocumentListDto, MeDto
from chatdocs.application.document_service import DocumentView, RangeNotSatisfiable, ReceivedFile
from chatdocs.domain.access.permissions import advertised_permissions
from chatdocs.domain.access.user import User
from chatdocs.domain.documents.document import DocumentStatus
from chatdocs.domain.errors import DocumentNotFound, FileTooLarge, RouteNotFound

fallback_router = APIRouter(prefix="/api/v1", dependencies=[Depends(current_auth)], include_in_schema=False)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(current_auth)], tags=["api"])

READ_CHUNK = 1024 * 1024
HEAD_BYTES = 1024


@router.get("/me", response_model=MeDto, response_model_by_alias=True)
async def me(request: Request, user: User = Depends(current_user)) -> MeDto:
    return MeDto(
        id=str(user.id),
        display_name=user.display_name,
        email=user.email,
        role=user.role.value,
        permissions=advertised_permissions(user),
        flags=sorted(container_of(request).settings.flags),
    )


async def _receive(upload: UploadFile, max_bytes: int) -> ReceivedFile:
    """Copy the upload to a temp file in 1 MB chunks, hashing on the way; stop as soon as the size limit is passed."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    digest, size, head = hashlib.sha256(), 0, b""
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await upload.read(READ_CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLarge(max_size_mb=max_bytes // (1024 * 1024))
                if len(head) < HEAD_BYTES:
                    head += chunk[: HEAD_BYTES - len(head)]
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        os.unlink(path)
        raise
    return ReceivedFile(upload.filename or "", path, size, digest.digest(), head)


@router.post("/documents", status_code=202, response_model=DocumentDto, response_model_by_alias=True)
async def upload_document(
    request: Request, file: UploadFile = File(...), force: bool = False, user: User = Depends(current_user)
) -> DocumentDto:
    c = container_of(request)
    received = await _receive(file, c.upload_policy.max_bytes)
    try:
        doc = await c.documents.upload(user, received, force=force, ip=client_ip(request))
    finally:
        os.unlink(received.local_path)
    return DocumentDto.of(DocumentView(doc, user.id, user.display_name, can_remove=True))


def _statuses(raw: list[str] | None) -> list[DocumentStatus] | None:
    if not raw:
        return None
    values = [v.strip().upper() for item in raw for v in item.split(",") if v.strip()]
    return [DocumentStatus(v) for v in values if v in DocumentStatus.__members__ and v != "REMOVED"] or None


@router.get("/documents", response_model=DocumentListDto, response_model_by_alias=True)
async def list_documents(
    request: Request,
    q: str | None = None,
    status: list[str] | None = Query(default=None),
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(current_user),
) -> DocumentListDto:
    result = await container_of(request).documents.list(
        user, name_query=q, statuses=_statuses(status), cursor=cursor, limit=limit
    )
    return DocumentListDto(items=[DocumentDto.of(v) for v in result.items], next_cursor=result.next_cursor)


@router.post("/documents/{document_id}/retry", status_code=202)
async def retry_document(request: Request, document_id: str, user: User = Depends(current_user)) -> dict:
    doc = await container_of(request).documents.retry(user, _uuid(document_id))
    return {"id": str(doc.id), "status": doc.status.value}  # the list endpoint (polled) returns the full row


@router.delete("/documents/{document_id}", status_code=202)
async def remove_document(request: Request, document_id: str, user: User = Depends(current_user)) -> dict:
    doc = await container_of(request).documents.remove(user, _uuid(document_id), ip=client_ip(request))
    return {"id": str(doc.id), "status": "REMOVED"}


def _content_disposition(name: str) -> str:
    ascii_name = name.encode("ascii", "ignore").decode().replace('"', "") or "document.pdf"
    return f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


@router.get("/documents/{document_id}/file")
async def document_file(request: Request, document_id: str, user: User = Depends(current_user)) -> Response:
    """US-305 / D3: streamed from object storage with Range support, so PDF.js loads only the pages it shows."""
    try:
        sl = await container_of(request).documents.open_file(user, _uuid(document_id), request.headers.get("range"))
    except RangeNotSatisfiable as e:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{e.total}"})
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(sl.end - sl.start + 1),
        "Cache-Control": "private, max-age=300",
        "Content-Disposition": _content_disposition(sl.file_name),
    }
    if sl.partial:
        headers["Content-Range"] = f"bytes {sl.start}-{sl.end}/{sl.total}"
    return StreamingResponse(
        sl.body, status_code=206 if sl.partial else 200, media_type="application/pdf", headers=headers
    )


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise DocumentNotFound() from None


# Mounted last (main.py): unknown /api/v1 paths go through the auth dependency first, so an anonymous caller gets
# 401 (not 404) and cannot probe which routes exist (default deny, T102.3).
@fallback_router.api_route("/{unknown_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def unknown_api_route(unknown_path: str) -> None:
    raise RouteNotFound()
