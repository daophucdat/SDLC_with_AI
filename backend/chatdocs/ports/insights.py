"""Ports for metrics (US-401) and evaluation runs (US-402)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from chatdocs.domain.evaluation.test_set import TestCase


class MetricsRepository(Protocol):
    async def compute_day(self, day: date) -> dict[str, float]:
        """Aggregate analytics.event for one UTC day (T401.1). Counts only — no content is read."""
        ...

    async def save_day(self, day: date, values: dict[str, float]) -> None: ...

    async def daily(self, since: date) -> dict[date, dict[str, float]]: ...

    async def weekly_active_users(self, since: date) -> dict[date, int]:
        """Distinct user_id_hash with question_submitted per ISO week (key = Monday)."""
        ...

    async def active_accounts(self) -> int: ...

    async def ensure_partitions(self, today: date, months_ahead: int, keep_months: int) -> list[str]:
        """Create monthly partitions ahead, drop ones older than `keep_months` (T-EN08.1). Returns actions done."""
        ...


@dataclass(frozen=True)
class EvaluationRun:
    id: UUID
    status: str  # queued | running | done | failed | timeout
    done: int
    total: int
    created_by: UUID | None


@dataclass(frozen=True)
class EvaluationResult:
    case: TestCase
    answer_text: str
    status: str
    citations: list[dict[str, Any]]
    latency_ms: int


class EvaluationRepository(Protocol):
    async def create_run(self, run_id: UUID, name: str, cases: list[TestCase], created_by: UUID) -> None: ...

    async def get_run(self, run_id: UUID) -> EvaluationRun | None: ...

    async def cases(self, run_id: UUID) -> list[tuple[UUID, TestCase]]: ...

    async def done_case_ids(self, run_id: UUID) -> set[UUID]: ...

    async def save_result(self, run_id: UUID, case_id: UUID, result: EvaluationResult) -> None: ...

    async def set_status(self, run_id: UUID, status: str, now: datetime) -> None: ...

    async def results(self, run_id: UUID) -> list[EvaluationResult]: ...
