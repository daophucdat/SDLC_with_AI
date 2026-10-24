"""RFC 9457 problem+json responses with a stable `code` (dev_tasks.md §0.6) and a `traceId`."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from chatdocs.domain.errors import DomainError
from chatdocs.platform.logging import get_logger

log = get_logger("chatdocs.http")

STATUS = {
    "AUTH_REQUIRED": 401,
    "FORBIDDEN_ROLE": 403,
    "FORBIDDEN": 403,
    "CSRF_INVALID": 403,
    "RATE_LIMITED": 429,
    "FILE_NOT_PDF": 415,
    "FILE_TOO_LARGE": 413,
    "DUPLICATE_DOCUMENT": 409,
    "DOC_NOT_FOUND": 404,
    "INVALID_STATE": 409,
    "VALIDATION_ERROR": 400,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
    "IDP_ERROR": 502,
    "QUESTION_INVALID": 400,
    "NO_READY_DOCUMENTS": 409,
    "AI_BUSY": 503,
    "ALREADY_SUBMITTED": 409,
    "EVENT_INVALID": 400,
    "TESTSET_INVALID": 400,
    "INTERNAL": 500,
}


def problem(request: Request, code: str, detail: str | None = None, **extra) -> JSONResponse:
    status = STATUS.get(code, 500)
    body = {
        "type": f"https://chatdocs.internal/errors/{code.lower()}",
        "title": code,
        "status": status,
        "code": code,
        "traceId": getattr(request.state, "trace_id", None),
    }
    if detail:
        body["detail"] = detail
    body.update(extra)
    headers = {}
    if code == "AUTH_REQUIRED":
        headers["WWW-Authenticate"] = 'Cookie realm="chatdocs"'
    if code == "RATE_LIMITED" and "retryAfter" in extra:
        headers["Retry-After"] = str(extra["retryAfter"])
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return problem(request, exc.code, **exc.details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [".".join(str(p) for p in e.get("loc", ())) for e in exc.errors()]
    return problem(request, "VALIDATION_ERROR", fields=fields)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "INTERNAL")
    return problem(request, code)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error(
        "unhandled_error",
        path=request.url.path,
        error_type=type(exc).__name__,
        trace_id=getattr(request.state, "trace_id", None),
    )
    return problem(request, "INTERNAL")
