"""Background jobs (SAD §2.2 table, ADR-05)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID


class JobType(str, Enum):
    PROCESS_DOCUMENT = "process_document"
    PURGE_DOCUMENT = "purge_document"
    RUN_EVALUATION = "run_evaluation"
    SWEEP_SESSIONS = "sweep_sessions"
    ROLLUP_METRICS = "rollup_metrics"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class Job:
    id: UUID
    type: JobType
    payload: dict[str, Any]
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    run_after: datetime | None = None
    created_at: datetime | None = field(default=None, compare=False)


# Retry schedule per job type: delay before attempt n+1 (index = attempts already made - 1).
RETRY_DELAYS: dict[JobType, list[timedelta]] = {
    # SAD §2.2: "3 lần thử lại, backoff 30 s / 2 phút / 10 phút; sau đó ERROR" → 1 attempt + 3 retries
    JobType.PROCESS_DOCUMENT: [timedelta(seconds=30), timedelta(minutes=2), timedelta(minutes=10)],
    # 5 retries spread over ~5.5 h, well inside the 24 h purge deadline (SEC-06)
    JobType.PURGE_DOCUMENT: [timedelta(minutes=m) for m in (1, 5, 15, 60, 240)],
    JobType.ROLLUP_METRICS: [timedelta(minutes=5), timedelta(minutes=15)],
    JobType.RUN_EVALUATION: [],
    JobType.SWEEP_SESSIONS: [],
}
TIMEOUTS: dict[JobType, timedelta] = {
    JobType.PROCESS_DOCUMENT: timedelta(minutes=10),
    JobType.PURGE_DOCUMENT: timedelta(minutes=5),
    JobType.RUN_EVALUATION: timedelta(minutes=60),
    JobType.SWEEP_SESSIONS: timedelta(minutes=2),
    JobType.ROLLUP_METRICS: timedelta(minutes=10),
}
CONCURRENCY: dict[JobType, int] = {
    JobType.PROCESS_DOCUMENT: 2,  # large PDFs are RAM-heavy
    JobType.PURGE_DOCUMENT: 1,
    JobType.RUN_EVALUATION: 1,
    JobType.SWEEP_SESSIONS: 1,
    JobType.ROLLUP_METRICS: 1,
}


def next_run_after(job_type: JobType, attempts_made: int, now: datetime) -> datetime | None:
    """When to retry after a failure, or None when the job has used all its attempts."""
    delays = RETRY_DELAYS[job_type]
    if attempts_made - 1 < len(delays):
        return now + delays[attempts_made - 1]
    return None
