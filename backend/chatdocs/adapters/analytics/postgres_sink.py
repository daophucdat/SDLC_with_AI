"""Batching event writer (T-EN08.2): in-memory queue, flushed every 50 events or 2 s. A failed write is counted and
dropped — analytics must never fail or slow down a user request."""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from chatdocs.application.analytics_service import EventRecord
from chatdocs.platform import metrics
from chatdocs.platform.logging import get_logger

log = get_logger("chatdocs.analytics")

_INSERT = text("""
    INSERT INTO analytics.event (name, ts, user_id_hash, session_id, app_version, props)
    VALUES (:name, :ts, :uh, :sid, :ver, CAST(:props AS jsonb))""")


class PostgresEventWriter:
    def __init__(
        self, engine: AsyncEngine, *, batch_size: int = 50, flush_seconds: float = 2.0, max_buffer: int = 5000
    ):
        self._e, self._batch, self._every = engine, batch_size, flush_seconds
        self._queue: asyncio.Queue[EventRecord] = asyncio.Queue(maxsize=max_buffer)
        self._task: asyncio.Task | None = None

    def submit(self, record: EventRecord) -> bool:
        try:
            self._queue.put_nowait(record)
            return True
        except asyncio.QueueFull:
            return False

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush(self._drain())  # write what is left on shutdown

    def _drain(self, limit: int | None = None) -> list[EventRecord]:
        out: list[EventRecord] = []
        while not self._queue.empty() and (limit is None or len(out) < limit):
            out.append(self._queue.get_nowait())
        return out

    async def _run(self) -> None:
        while True:
            try:
                first = await asyncio.wait_for(self._queue.get(), timeout=self._every)
            except asyncio.TimeoutError:
                continue
            batch = [first, *self._drain(self._batch - 1)]
            if len(batch) < self._batch:
                await asyncio.sleep(min(self._every, 0.2))  # let a burst accumulate
                batch += self._drain(self._batch - len(batch))
            await self._flush(batch)

    async def _flush(self, batch: list[EventRecord]) -> None:
        if not batch:
            return
        try:
            async with self._e.begin() as c:
                await c.execute(
                    _INSERT,
                    [
                        {
                            "name": r.name,
                            "ts": r.ts,
                            "uh": r.user_id_hash,
                            "sid": r.session_id,
                            "ver": r.app_version,
                            "props": json.dumps(r.props),
                        }
                        for r in batch
                    ],
                )
        except Exception as e:  # noqa: BLE001
            metrics.ANALYTICS_DROPPED.inc(len(batch))
            log.warning("analytics_flush_failed", count=len(batch), error_type=type(e).__name__)


class MemoryEventWriter:
    """For tests and for `python -m` tools that do not need analytics."""

    def __init__(self) -> None:
        self.records: list[EventRecord] = []

    def submit(self, record: EventRecord) -> bool:
        self.records.append(record)
        return True
