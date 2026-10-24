"""Job runner (EN-04, ADR-05): claims jobs from PostgreSQL with SKIP LOCKED, runs them with per-type concurrency
limits and timeouts, retries with the backoff schedule from domain.jobs, and reports exhausted jobs."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable
from uuid import UUID

from chatdocs.domain.jobs import CONCURRENCY, TIMEOUTS, Job, JobType, next_run_after
from chatdocs.platform import metrics
from chatdocs.platform.logging import get_logger
from chatdocs.ports.clock import Clock
from chatdocs.ports.repositories import JobQueue

log = get_logger("chatdocs.worker")

Handler = Callable[[Job], Awaitable[None]]
OnExhausted = Callable[[Job], Awaitable[None]]


class JobRunner:
    def __init__(
        self,
        *,
        queue: JobQueue,
        clock: Clock,
        handlers: dict[JobType, Handler],
        on_exhausted: dict[JobType, OnExhausted] | None = None,
        poll_seconds: float = 5.0,
        worker_id: str | None = None,
    ) -> None:
        self._queue, self._clock, self._handlers = queue, clock, handlers
        self._on_exhausted = on_exhausted or {}
        self._poll = poll_seconds
        self.worker_id = worker_id or f"{socket.gethostname()}-{id(self):x}"
        self._sem = {t: asyncio.Semaphore(CONCURRENCY[t]) for t in handlers}
        self._wake = asyncio.Event()
        self._stopping = asyncio.Event()
        self._running: set[asyncio.Task] = set()

    def notify(self, *_args) -> None:
        """Called by the LISTEN/NOTIFY listener; wakes the claim loop immediately."""
        self._wake.set()

    async def run_once(self) -> bool:
        """Claim and start at most one job per type that has a free slot. Returns True if anything started."""
        started = False
        for job_type, sem in self._sem.items():
            if sem.locked():
                continue
            job = await self._queue.claim(self.worker_id, [job_type], self._clock.now())
            if job is None:
                continue
            await sem.acquire()
            task = asyncio.create_task(self._execute(job, sem))
            self._running.add(task)
            task.add_done_callback(self._running.discard)
            started = True
        return started

    async def _execute(self, job: Job, sem: asyncio.Semaphore) -> None:
        try:
            await asyncio.wait_for(self._handlers[job.type](job), timeout=TIMEOUTS[job.type].total_seconds())
            await self._queue.complete(job.id)
            metrics.JOBS.labels(job.type.value, "done").inc()
            log.info("job_done", job_id=str(job.id), job_type=job.type.value, attempts=job.attempts)
        except Exception as e:  # noqa: BLE001 — every failure goes through the retry policy
            await self._handle_failure(job, e)
        finally:
            sem.release()
            self._wake.set()

    async def _handle_failure(self, job: Job, error: Exception) -> None:
        reason = "timeout" if isinstance(error, asyncio.TimeoutError) else type(error).__name__
        retry_at = next_run_after(job.type, job.attempts, self._clock.now())
        if retry_at is not None:
            await self._queue.retry_later(job.id, reason, retry_at)
            log.warning("job_retry", job_id=str(job.id), job_type=job.type.value, attempts=job.attempts, reason=reason)
            return
        await self._queue.fail(job.id, reason)
        metrics.JOB_FAILURES.labels(job.type.value).inc()
        log.error("job_failed", job_id=str(job.id), job_type=job.type.value, attempts=job.attempts, reason=reason)
        hook = self._on_exhausted.get(job.type)
        if hook:
            await hook(job)

    async def serve(self) -> None:
        requeued = await self._queue.requeue_stale(self._clock.now())
        if requeued:
            log.warning("jobs_requeued", count=requeued)
        while not self._stopping.is_set():
            while await self.run_once():
                pass
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self._poll)
            except asyncio.TimeoutError:
                pass
        if self._running:
            await asyncio.gather(*self._running, return_exceptions=True)

    def stop(self) -> None:
        self._stopping.set()
        self._wake.set()

    async def drain(self) -> None:
        """Test helper: wait for all started jobs."""
        while self._running:
            await asyncio.gather(*list(self._running), return_exceptions=True)


def document_id_of(job: Job) -> UUID:
    return UUID(str(job.payload["document_id"]))
