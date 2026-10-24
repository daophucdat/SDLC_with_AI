from __future__ import annotations

import asyncio
from datetime import timedelta

from chatdocs.adapters.jobs.runner import JobRunner
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import Job, JobStatus, JobType
from tests.fakes import FixedClock, MemJobQueue


def job(n: int = 0) -> Job:
    return Job(id=uuid7(), type=JobType.PROCESS_DOCUMENT, payload={"document_id": str(uuid7()), "n": n})


async def test_successful_job_is_completed():
    q, clock, seen = MemJobQueue(), FixedClock(), []

    async def handler(j):
        seen.append(j.payload["n"])

    q.add(job(1))
    runner = JobRunner(queue=q, clock=clock, handlers={JobType.PROCESS_DOCUMENT: handler})
    assert await runner.run_once()
    await runner.drain()
    assert seen == [1]
    assert all(j.status is JobStatus.DONE for j in q.jobs.values())


async def test_failures_follow_backoff_then_call_on_exhausted():
    q, clock, exhausted = MemJobQueue(), FixedClock(), []

    async def handler(j):
        raise RuntimeError("embedder down")

    async def give_up(j):
        exhausted.append(j.id)

    j = job()
    q.add(j)
    runner = JobRunner(
        queue=q,
        clock=clock,
        handlers={JobType.PROCESS_DOCUMENT: handler},
        on_exhausted={JobType.PROCESS_DOCUMENT: give_up},
    )
    delays = []
    for _ in range(4):
        start = clock.now()
        assert await runner.run_once()
        await runner.drain()
        current = q.jobs[j.id]
        if current.status is JobStatus.QUEUED:
            delays.append(current.run_after - start)
            clock.t = current.run_after
    assert delays == [timedelta(seconds=30), timedelta(minutes=2), timedelta(minutes=10)]
    assert q.jobs[j.id].status is JobStatus.FAILED and q.jobs[j.id].attempts == 4
    assert exhausted == [j.id]
    assert q.errors[j.id] == "RuntimeError"


async def test_concurrency_limit_two_process_jobs():
    q, clock = MemJobQueue(), FixedClock()
    release, running, peak = asyncio.Event(), [0], [0]

    async def handler(j):
        running[0] += 1
        peak[0] = max(peak[0], running[0])
        await release.wait()
        running[0] -= 1

    for i in range(5):
        q.add(job(i))
    runner = JobRunner(queue=q, clock=clock, handlers={JobType.PROCESS_DOCUMENT: handler})
    while await runner.run_once():
        pass
    await asyncio.sleep(0.05)  # let the started tasks reach their await
    assert peak[0] == 2  # large PDFs are RAM-heavy: at most 2 at a time (SAD §2.2)
    release.set()
    await runner.drain()
    while await runner.run_once():
        await runner.drain()
    assert all(j.status is JobStatus.DONE for j in q.jobs.values())


async def test_stale_running_jobs_are_requeued_on_start():
    q, clock = MemJobQueue(), FixedClock()
    j = job()
    q.add(j)
    await q.claim("dead-worker", [JobType.PROCESS_DOCUMENT], clock.now())
    clock.advance(minutes=11)
    assert await q.requeue_stale(clock.now()) == 1
    assert q.jobs[j.id].status is JobStatus.QUEUED
