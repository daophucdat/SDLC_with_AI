"""US-401 weekly metrics, US-402 evaluation runs, and the housekeeping jobs that keep them (and SEC-06) honest."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from chatdocs.application.access_service import AuthContext
from chatdocs.application.qa_service import QuestionAnsweringService
from chatdocs.domain.access.permissions import Action, can
from chatdocs.domain.access.user import User
from chatdocs.domain.errors import Forbidden, InvalidState, RouteNotFound
from chatdocs.domain.evaluation.test_set import TestCase, parse_rows
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import Job, JobType
from chatdocs.domain.metrics.weekly import WeeklyMetric, fold_weeks, week_start
from chatdocs.platform.logging import get_logger
from chatdocs.ports.clock import Clock
from chatdocs.ports.insights import EvaluationRepository, EvaluationResult, EvaluationRun, MetricsRepository
from chatdocs.ports.repositories import AuditLog, JobQueue

log = get_logger("chatdocs.insights")

ALLOWED_WEEKS = (4, 8, 12)
EVALUATION_DEADLINE_S = 58 * 60  # AC-402.3: stop before the 60-min job timeout and keep what is done


class MetricsService:
    def __init__(self, *, repo: MetricsRepository, clock: Clock) -> None:
        self._repo, self._clock = repo, clock

    async def weekly(self, user: User, weeks: int) -> list[WeeklyMetric]:
        if not can(user, Action.METRICS_VIEW):
            raise Forbidden()  # AC-401.2
        weeks = weeks if weeks in ALLOWED_WEEKS else 4
        today = self._clock.now().date()
        since = week_start(today) - timedelta(weeks=weeks - 1)
        daily = await self._repo.daily(since)
        wau = await self._repo.weekly_active_users(since)
        accounts = await self._repo.active_accounts()
        return fold_weeks(daily, wau, accounts, weeks, today)

    async def rollup(self, day: date | None = None) -> dict[str, float]:
        """Job rollup_metrics (01:00 daily, T401.1): yesterday by default; idempotent (upsert)."""
        day = day or (self._clock.now().date() - timedelta(days=1))
        values = await self._repo.compute_day(day)
        await self._repo.save_day(day, values)
        return values

    async def maintain_partitions(self) -> list[str]:
        return await self._repo.ensure_partitions(self._clock.now().date(), months_ahead=2, keep_months=13)


@dataclass(frozen=True)
class RunStatus:
    run_id: UUID
    status: str
    done: int
    total: int


class EvaluationService:
    def __init__(
        self,
        *,
        repo: EvaluationRepository,
        jobs: JobQueue,
        qa: QuestionAnsweringService | None,
        audit: AuditLog,
        clock: Clock,
    ) -> None:
        self._repo, self._jobs, self._qa, self._audit, self._clock = repo, jobs, qa, audit, clock

    async def start(self, auth: AuthContext, file_name: str, rows: list[list[Any]], ip: str | None) -> RunStatus:
        if not can(auth.user, Action.EVALUATION_RUN):
            raise Forbidden()
        cases = parse_rows(rows)  # TESTSET_INVALID {row, column} (AC-402.2)
        run_id = uuid7()
        await self._repo.create_run(run_id, file_name[:200] or "test-set", cases, auth.user.id)
        await self._jobs.enqueue(Job(id=uuid7(), type=JobType.RUN_EVALUATION, payload={"run_id": str(run_id)}))
        await self._audit.record(
            action="evaluation_run", actor_id=auth.user.id, target_type="evaluation", target_id=str(run_id), ip=ip
        )
        return RunStatus(run_id, "queued", 0, len(cases))

    async def _visible_run(self, user: User, run_id: UUID) -> EvaluationRun:
        if not can(user, Action.EVALUATION_RUN):
            raise Forbidden()
        run = await self._repo.get_run(run_id)
        if run is None:
            raise RouteNotFound()
        return run

    async def status(self, user: User, run_id: UUID) -> RunStatus:
        run = await self._visible_run(user, run_id)
        return RunStatus(run.id, run.status, run.done, run.total)

    async def results(self, user: User, run_id: UUID) -> list[EvaluationResult]:
        run = await self._visible_run(user, run_id)
        if run.status not in ("done", "timeout", "failed"):
            raise InvalidState()  # V3 → 409 until the run has finished
        return await self._repo.results(run_id)

    async def execute(self, run_id: UUID, *, deadline_s: float = EVALUATION_DEADLINE_S) -> str:
        """Job run_evaluation: calls the Q&A pipeline directly (no HTTP); resumable — finished cases are skipped."""
        assert self._qa is not None, "the worker wires the Q&A service"
        t0 = time.monotonic()
        await self._repo.set_status(run_id, "running", self._clock.now())
        done = await self._repo.done_case_ids(run_id)
        for case_id, case in await self._repo.cases(run_id):
            if case_id in done:
                continue
            if time.monotonic() - t0 > deadline_s:
                await self._repo.set_status(run_id, "timeout", self._clock.now())
                return "timeout"
            await self._repo.save_result(run_id, case_id, await self._answer(case))
        await self._repo.set_status(run_id, "done", self._clock.now())
        return "done"

    async def _answer(self, case: TestCase) -> EvaluationResult:
        try:
            out, latency = await self._qa.answer_for_evaluation(case.question)
        except Exception as e:  # noqa: BLE001 — one failing question must not stop the run
            log.warning("evaluation_case_failed", ordinal=case.ordinal, error_type=type(e).__name__)
            return EvaluationResult(case, "", "FAILED", [], 0)
        status = out.status.value if out.status else "FAILED"
        if out.reason:
            status = f"{status}:{out.reason.value}"
        cites = [{"index": c.index, "file": c.file_name, "page": c.page_number} for c in out.citations]
        return EvaluationResult(case, out.text, status, cites, latency)
