"""Metrics rollups (US-401, T401.1), analytics partitions (T-EN08.1) and evaluation runs (US-402)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from chatdocs.domain.evaluation.test_set import TestCase
from chatdocs.domain.ids import uuid7
from chatdocs.platform.logging import get_logger
from chatdocs.ports.insights import EvaluationResult, EvaluationRun

log = get_logger("chatdocs.insights")

# Counts and latencies only: no column of analytics.event can hold text (allow-list, §0.7) — AC-401.3.
_DAY_SQL = text("""
    SELECT
      count(DISTINCT user_id_hash) FILTER (WHERE name = 'question_submitted')                    AS active_users,
      count(*) FILTER (WHERE name = 'question_submitted')                                         AS questions,
      count(*) FILTER (WHERE name = 'answer_completed')                                           AS answers,
      count(*) FILTER (WHERE name = 'answer_completed' AND (props->>'is_not_found')::boolean)     AS not_found,
      count(*) FILTER (WHERE name = 'answer_feedback_submitted' AND props->>'value' = 'HELPFUL')   AS helpful,
      count(*) FILTER (WHERE name = 'answer_feedback_submitted')                                  AS feedback_total,
      percentile_cont(0.95) WITHIN GROUP (ORDER BY (props->>'latency_ms')::int)
        FILTER (WHERE name = 'answer_completed' AND NOT (props->>'is_not_found')::boolean)        AS p95_latency_ms,
      count(*) FILTER (WHERE name = 'answer_failed')                                              AS errors
    FROM analytics.event
    WHERE ts >= :start AND ts < :end""")


def _month_start(d: date, offset: int = 0) -> date:
    m = d.month - 1 + offset
    return date(d.year + m // 12, m % 12 + 1, 1)


class PgMetricsRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def compute_day(self, day: date) -> dict[str, float]:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        async with self._e.connect() as c:
            row = (await c.execute(_DAY_SQL, {"start": start, "end": start + timedelta(days=1)})).one()
        return {k: float(v) for k, v in row._mapping.items() if v is not None}

    async def save_day(self, day: date, values: dict[str, float]) -> None:
        if not values:
            return
        async with self._e.begin() as c:
            await c.execute(
                text("""
                INSERT INTO analytics.daily_rollup (day, metric, value) VALUES (:d, :m, :v)
                ON CONFLICT (day, metric) DO UPDATE SET value = EXCLUDED.value"""),
                [{"d": day, "m": k, "v": v} for k, v in values.items()],
            )

    async def daily(self, since: date) -> dict[date, dict[str, float]]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text("SELECT day, metric, value FROM analytics.daily_rollup WHERE day >= :s"), {"s": since}
                )
            ).all()
        out: dict[date, dict[str, float]] = {}
        for r in rows:
            out.setdefault(r.day, {})[r.metric] = float(r.value)
        return out

    async def weekly_active_users(self, since: date) -> dict[date, int]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text("""
                SELECT (date_trunc('week', ts AT TIME ZONE 'UTC'))::date AS monday, count(DISTINCT user_id_hash) AS n
                  FROM analytics.event
                 WHERE name = 'question_submitted' AND ts >= :s
                 GROUP BY 1"""),
                    {"s": datetime(since.year, since.month, since.day, tzinfo=timezone.utc)},
                )
            ).all()
        return {r.monday: int(r.n) for r in rows}

    async def active_accounts(self) -> int:
        # DQ-04: the WAU denominator is app_user.active (shown on the metrics page).
        async with self._e.connect() as c:
            return int((await c.execute(text("SELECT count(*) FROM access.app_user WHERE active"))).scalar_one())

    async def ensure_partitions(self, today: date, months_ahead: int, keep_months: int) -> list[str]:
        done: list[str] = []
        for offset in range(1, months_ahead + 1):  # future months only: the DEFAULT partition holds the current one
            start, end = _month_start(today, offset), _month_start(today, offset + 1)
            name = f"event_{start:%Y%m}"
            try:
                async with self._e.begin() as c:
                    exists = (
                        await c.execute(text("SELECT to_regclass(:n) IS NOT NULL"), {"n": f"analytics.{name}"})
                    ).scalar_one()
                    if not exists:
                        await c.execute(
                            text(
                                f"CREATE TABLE analytics.{name} PARTITION OF analytics.event "
                                f"FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')"
                            )
                        )
                        done.append(f"created {name}")
            except Exception as e:  # noqa: BLE001 — e.g. rows for that range already in DEFAULT
                log.warning("partition_create_failed", partition=name, error_type=type(e).__name__)
        oldest_kept = _month_start(today, -keep_months)
        async with self._e.begin() as c:
            names = (
                await c.execute(text("""
                SELECT child.relname FROM pg_inherits
                  JOIN pg_class parent ON parent.oid = pg_inherits.inhparent
                  JOIN pg_class child ON child.oid = pg_inherits.inhrelid
                  JOIN pg_namespace ns ON ns.oid = parent.relnamespace
                 WHERE ns.nspname = 'analytics' AND parent.relname = 'event' AND child.relname ~ '^event_[0-9]{6}$'"""))
            ).scalars()
            for n in list(names):
                y, m = int(n[6:10]), int(n[10:12])
                if date(y, m, 1) < oldest_kept:  # OQ-016: 13 months of analytics
                    await c.execute(text(f'DROP TABLE analytics."{n}"'))
                    done.append(f"dropped {n}")
        return done


class PgEvaluationRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._e = engine

    async def create_run(self, run_id: UUID, name: str, cases: list[TestCase], created_by: UUID) -> None:
        set_id = uuid7()
        async with self._e.begin() as c:
            await c.execute(
                text("INSERT INTO evaluation.test_set (id, name, created_by) VALUES (:id, :n, :u)"),
                {"id": set_id, "n": name, "u": created_by},
            )
            await c.execute(
                text("""
                INSERT INTO evaluation.test_case
                       (id, test_set_id, ordinal, question, expected_answer, expects_not_found)
                VALUES (:id, :s, :o, :q, :e, :nf)"""),
                [
                    {
                        "id": uuid7(),
                        "s": set_id,
                        "o": tc.ordinal,
                        "q": tc.question,
                        "e": tc.expected_answer,
                        "nf": tc.expects_not_found,
                    }
                    for tc in cases
                ],
            )
            await c.execute(
                text("""
                INSERT INTO evaluation.run (id, test_set_id, status, done_count, total)
                VALUES (:id, :s, 'queued', 0, :t)"""),
                {"id": run_id, "s": set_id, "t": len(cases)},
            )

    async def get_run(self, run_id: UUID) -> EvaluationRun | None:
        async with self._e.connect() as c:
            row = (
                await c.execute(
                    text("""
                SELECT r.id, r.status, r.done_count, r.total, s.created_by
                  FROM evaluation.run r JOIN evaluation.test_set s ON s.id = r.test_set_id WHERE r.id = :id"""),
                    {"id": run_id},
                )
            ).first()
        return EvaluationRun(row.id, row.status, row.done_count or 0, row.total, row.created_by) if row else None

    async def cases(self, run_id: UUID) -> list[tuple[UUID, TestCase]]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text("""
                SELECT tc.id, tc.ordinal, tc.question, tc.expected_answer, tc.expects_not_found
                  FROM evaluation.run r JOIN evaluation.test_case tc ON tc.test_set_id = r.test_set_id
                 WHERE r.id = :id ORDER BY tc.ordinal, tc.id"""),
                    {"id": run_id},
                )
            ).all()
        return [(r.id, TestCase(r.ordinal, r.question, r.expected_answer, r.expects_not_found)) for r in rows]

    async def done_case_ids(self, run_id: UUID) -> set[UUID]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(text("SELECT test_case_id FROM evaluation.result WHERE run_id = :id"), {"id": run_id})
            ).all()
        return {r.test_case_id for r in rows}

    async def save_result(self, run_id: UUID, case_id: UUID, result: EvaluationResult) -> None:
        async with self._e.begin() as c:
            await c.execute(
                text("""
                INSERT INTO evaluation.result (run_id, test_case_id, answer_text, status, citations, latency_ms)
                VALUES (:r, :c, :a, :s, CAST(:ci AS jsonb), :l)
                ON CONFLICT (run_id, test_case_id) DO NOTHING"""),
                {
                    "r": run_id,
                    "c": case_id,
                    "a": result.answer_text,
                    "s": result.status,
                    "ci": json.dumps(result.citations, ensure_ascii=False),
                    "l": result.latency_ms,
                },
            )
            await c.execute(text("UPDATE evaluation.run SET done_count = done_count + 1 WHERE id = :r"), {"r": run_id})

    async def set_status(self, run_id: UUID, status: str, now: datetime) -> None:
        col = "started_at" if status == "running" else "finished_at"
        async with self._e.begin() as c:
            await c.execute(
                text(f"UPDATE evaluation.run SET status = :s, {col} = :now WHERE id = :id"),
                {"id": run_id, "s": status, "now": now},
            )

    async def results(self, run_id: UUID) -> list[EvaluationResult]:
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text("""
                SELECT tc.ordinal, tc.question, tc.expected_answer, tc.expects_not_found,
                       res.answer_text, res.status, res.citations, res.latency_ms
                  FROM evaluation.run r JOIN evaluation.test_case tc ON tc.test_set_id = r.test_set_id
                  LEFT JOIN evaluation.result res ON res.run_id = r.id AND res.test_case_id = tc.id
                 WHERE r.id = :id ORDER BY tc.ordinal"""),
                    {"id": run_id},
                )
            ).all()
        out = []
        for r in rows:
            cites = r.citations if isinstance(r.citations, list) else json.loads(r.citations or "[]")
            out.append(
                EvaluationResult(
                    TestCase(r.ordinal, r.question, r.expected_answer, r.expects_not_found),
                    r.answer_text or "",
                    r.status or "NOT_RUN",
                    cites,
                    r.latency_ms or 0,
                )
            )
        return out
