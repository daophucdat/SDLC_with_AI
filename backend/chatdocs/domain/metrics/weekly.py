"""US-401: fold daily rollups into ISO weeks (Monday → Sunday) and compare them with the OKR targets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# daily_rollup.metric names written by the rollup job (T401.1)
DAILY_METRICS = (
    "active_users",
    "questions",
    "answers",
    "not_found",
    "helpful",
    "feedback_total",
    "p95_latency_ms",
    "errors",
)

# OKR targets shown next to each number (PRD §5.2)
TARGETS = {"wauRate": 0.6, "helpfulRate": 0.7, "p95LatencyMs": 30000}  # metrics.html: KR3.1, KR3.2, KR1.2


@dataclass(frozen=True)
class WeeklyMetric:
    week: str  # ISO week, e.g. "2026-W46"
    week_start: date
    active_users: int
    wau_rate: float
    questions: int
    not_found_rate: float
    helpful_rate: float | None
    p95_latency_ms: int | None


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def fold_weeks(
    daily: dict[date, dict[str, float]],
    weekly_active_users: dict[date, int],
    active_accounts: int,
    weeks: int,
    today: date,
) -> list[WeeklyMetric]:
    """`daily[day][metric]`; `weekly_active_users[monday]` must be a distinct count over the whole week (a sum of daily
    distinct counts would count the same person once per day). Weeks with no data are returned as zeros, newest
    first, so the page always shows `weeks` rows."""
    out: list[WeeklyMetric] = []
    start = week_start(today)
    for i in range(weeks):
        monday = start - timedelta(weeks=i)
        days = [monday + timedelta(days=k) for k in range(7)]
        rows = [daily[d] for d in days if d in daily]

        def total(metric: str, rows=rows) -> float:
            return sum(r.get(metric, 0) for r in rows)

        questions, answers = int(total("questions")), int(total("answers"))
        fb = total("feedback_total")
        p95s = [r["p95_latency_ms"] for r in rows if r.get("p95_latency_ms")]
        wau = weekly_active_users.get(monday, 0)
        out.append(
            WeeklyMetric(
                week=iso_week(monday),
                week_start=monday,
                active_users=wau,
                wau_rate=round(wau / active_accounts, 4) if active_accounts else 0.0,
                questions=questions,
                not_found_rate=round(total("not_found") / answers, 4) if answers else 0.0,
                helpful_rate=round(total("helpful") / fb, 4) if fb else None,
                # Approximation: the worst daily p95 of the week (an exact weekly p95 needs the raw events).
                p95_latency_ms=int(max(p95s)) if p95s else None,
            )
        )
    return out
