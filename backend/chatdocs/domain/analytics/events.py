"""Analytics allow-list (dev_tasks.md §0.7, T-EN08.3). An event is accepted only if its name is listed and every prop
is a listed key of the right type. There is no free-text prop, so question / answer / document text can never be
stored (AC-401.3, TC-08)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chatdocs.domain.errors import EventInvalid


@dataclass(frozen=True)
class Enum_:
    values: frozenset[str]
    nullable: bool = False


_BOOL, _INT, _NUM = bool, int, float
_LANG = Enum_(frozenset({"vi", "en"}))
_NOT_FOUND = Enum_(frozenset({"NO_CHUNKS", "MODEL_NOT_FOUND", "INVALID_CITATIONS"}), nullable=True)

SCHEMA: dict[str, dict[str, Any]] = {
    "session_started": {"is_first_session": _BOOL},
    "access_denied": {"reason": Enum_(frozenset({"no_group", "inactive"}))},
    "document_upload_started": {"file_size_mb": _NUM, "batch_size": _INT},
    "document_upload_failed": {"reason": Enum_(frozenset({"not_pdf", "too_large", "network", "password", "corrupt"}))},
    "document_processing_completed": {
        "page_count": _INT,
        "duration_ms": _INT,
        "status": Enum_(frozenset({"ready", "no_text", "error"})),
    },
    "document_removed": {"role": Enum_(frozenset({"uploader", "lead"})), "doc_age_days": _INT},
    "question_submitted": {
        "language": _LANG,
        "question_length": _INT,
        "ready_doc_count": _INT,
        "is_suggested": _BOOL,
        "turn_index": _INT,
    },
    "answer_completed": {
        "latency_ms": _INT,
        "first_token_ms": _INT,
        "citation_count": _INT,
        "distinct_docs_cited": _INT,
        "is_not_found": _BOOL,
        "not_found_reason": _NOT_FOUND,
    },
    "answer_failed": {"error_type": Enum_(frozenset({"timeout", "service_error", "network"}))},
    "answer_stopped": {"elapsed_ms": _INT},
    "citation_clicked": {"citation_index": _INT, "doc_removed": _BOOL},
    "answer_copied": {"with_sources": _BOOL},
    "answer_feedback_submitted": {
        "value": Enum_(frozenset({"HELPFUL", "NOT_HELPFUL"})),
        "reason": Enum_(frozenset({"wrong", "incomplete", "wrong_source", "other"}), nullable=True),
    },
}

# Props that may be absent / null (measured values that do not always exist).
OPTIONAL: dict[str, frozenset[str]] = {
    "answer_completed": frozenset({"first_token_ms", "not_found_reason"}),
    "answer_feedback_submitted": frozenset({"reason"}),
    "question_submitted": frozenset({"is_suggested"}),
}

# Only these may be sent by the browser through POST /events (T-EN08.4); the rest are emitted by the server.
FRONTEND_EVENTS = frozenset({"document_upload_started", "document_upload_failed", "citation_clicked", "answer_copied"})


def _type_ok(spec: Any, value: Any) -> bool:
    if isinstance(spec, Enum_):
        return (value is None and spec.nullable) or (isinstance(value, str) and value in spec.values)
    if spec is _BOOL:
        return isinstance(value, bool)
    if spec is _INT:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    if spec is _NUM:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
    return False


def validate_event(name: str, props: dict[str, Any] | None) -> dict[str, Any]:
    """Returns the props unchanged if valid; raises EventInvalid naming the first problem otherwise."""
    if name not in SCHEMA:
        raise EventInvalid(field="name")
    props = props or {}
    if not isinstance(props, dict):
        raise EventInvalid(field="props")
    spec = SCHEMA[name]
    for key, value in props.items():
        if key not in spec:
            raise EventInvalid(field=key)  # unknown keys are refused, never silently dropped
        if value is None and key in OPTIONAL.get(name, frozenset()):
            continue
        if not _type_ok(spec[key], value):
            raise EventInvalid(field=key)
    missing = set(spec) - set(props) - OPTIONAL.get(name, frozenset())
    if missing:
        raise EventInvalid(field=sorted(missing)[0])
    return props
