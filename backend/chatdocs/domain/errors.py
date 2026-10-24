"""Domain errors. Each carries a stable `code` (dev_tasks.md §0.6); the HTTP adapter maps codes to status codes."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code = "INTERNAL"

    def __init__(self, message: str = "", **details: Any) -> None:
        super().__init__(message or self.code)
        self.details = details


class AuthRequired(DomainError):
    code = "AUTH_REQUIRED"


class ForbiddenRole(DomainError):
    code = "FORBIDDEN_ROLE"


class Forbidden(DomainError):
    code = "FORBIDDEN"


class CsrfInvalid(DomainError):
    code = "CSRF_INVALID"


class FileNotPdf(DomainError):
    code = "FILE_NOT_PDF"


class FileTooLarge(DomainError):
    code = "FILE_TOO_LARGE"


class DuplicateDocument(DomainError):
    code = "DUPLICATE_DOCUMENT"


class DocumentNotFound(DomainError):
    code = "DOC_NOT_FOUND"


class InvalidState(DomainError):
    code = "INVALID_STATE"


class RouteNotFound(DomainError):
    code = "NOT_FOUND"


class IdentityProviderError(DomainError):
    code = "IDP_ERROR"


class QuestionInvalid(DomainError):
    code = "QUESTION_INVALID"


class NoReadyDocuments(DomainError):
    code = "NO_READY_DOCUMENTS"


class RateLimited(DomainError):
    code = "RATE_LIMITED"


class AiBusy(DomainError):
    code = "AI_BUSY"


class AlreadySubmitted(DomainError):
    code = "ALREADY_SUBMITTED"


class EventInvalid(DomainError):
    code = "EVENT_INVALID"


class TestsetInvalid(DomainError):
    code = "TESTSET_INVALID"
    __test__ = False  # not a pytest test class
