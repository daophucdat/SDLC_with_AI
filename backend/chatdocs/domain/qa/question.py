"""Question / Answer (US-301, US-302, US-304, US-310). Pure domain: validation, language detection, states."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from chatdocs.domain.errors import QuestionInvalid
from chatdocs.domain.ids import uuid7

MAX_QUESTION_CHARS = 2000
# Any Vietnamese letter with a diacritic (or đ) → the question is Vietnamese (T301.1)
_VI_CHARS = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE)


class Language(str, Enum):
    VI = "vi"
    EN = "en"


class AnswerStatus(str, Enum):
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    NOT_FOUND = "NOT_FOUND"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class NotFoundReason(str, Enum):
    NO_CHUNKS = "NO_CHUNKS"  # retrieval found nothing above τ — the LLM was not called (AC-304.4)
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"  # the LLM answered NOT_FOUND
    INVALID_CITATIONS = "INVALID_CITATIONS"  # ALG-3 rejected the answer (AC-303.3)


def detect_language(text: str) -> Language:
    return Language.VI if _VI_CHARS.search(text) else Language.EN


@dataclass(frozen=True)
class Question:
    id: UUID
    conversation_id: UUID
    text: str
    language: Language
    is_followup: bool
    asked_at: datetime

    @staticmethod
    def create(conversation_id: UUID, text: str, *, follow_up: bool, now: datetime) -> Question:
        body = (text or "").strip()
        if not body:
            raise QuestionInvalid(reason="empty")
        if len(body) > MAX_QUESTION_CHARS:
            raise QuestionInvalid(reason="too_long", maxLength=MAX_QUESTION_CHARS)
        return Question(uuid7(), conversation_id, body, detect_language(body), follow_up, now)


@dataclass(frozen=True)
class Turn:
    """One question + its answer, as replayed by US-308 and used as follow-up context (US-311)."""

    question_id: UUID
    question_text: str
    answer_id: UUID
    answer_text: str
    status: AnswerStatus
    citations: list  # list[Citation]
    feedback: str | None = None
