"""Scheduled housekeeping (worker): which periodic job is due — session sweep every 15 min (US-103 T103.1),
metrics rollup + analytics partitions daily (T401.1, T-EN08.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import Job, JobType
from chatdocs.ports.repositories import JobQueue


@dataclass(frozen=True)
class Schedule:
    job_type: JobType
    every: timedelta | None = None  # fixed interval, slot = start of the interval
    daily_at_hour: int | None = None  # once a day at this UTC hour


SCHEDULES = (
    Schedule(JobType.SWEEP_SESSIONS, every=timedelta(minutes=15)),
    # 01:00 Asia/Ho_Chi_Minh = 18:00 UTC of the previous day; rollup covers the previous UTC day either way.
    Schedule(JobType.ROLLUP_METRICS, daily_at_hour=18),
)


def slot_for(s: Schedule, now: datetime) -> str | None:
    """Identifier of the run that is due now, or None. Identical slots are enqueued once across all workers."""
    if s.every is not None:
        epoch = int(now.timestamp() // s.every.total_seconds())
        return f"{s.job_type.value}:{epoch}"
    if s.daily_at_hour is not None and now.hour >= s.daily_at_hour:
        return f"{s.job_type.value}:{now.date().isoformat()}"
    return None


async def enqueue_due(queue: JobQueue, now: datetime) -> list[str]:
    added = []
    for s in SCHEDULES:
        slot = slot_for(s, now)
        if slot and await queue.enqueue_once(Job(id=uuid7(), type=s.job_type, payload={"slot": slot}), slot):
            added.append(slot)
    return added
