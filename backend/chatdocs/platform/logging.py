"""Structured JSON logs with content redaction (TC-08, QAS-06).

Questions, answers and document text never reach logs."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

CONTENT_KEYS = frozenset({"text", "content", "question", "answer", "excerpt", "prompt", "body", "page_text"})
REDACTED = "[redacted]"


def redact_content(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict):
        if key.lower() in CONTENT_KEYS:
            event_dict[key] = REDACTED
        elif isinstance(event_dict[key], dict):
            event_dict[key] = {k: (REDACTED if k.lower() in CONTENT_KEYS else v) for k, v in event_dict[key].items()}
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_content,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "chatdocs") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
