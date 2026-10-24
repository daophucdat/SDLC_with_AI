"""E1 events (EN-08), M1 weekly metrics (US-401), V1 → V3 evaluation runs (US-402)."""

from __future__ import annotations

import os
import tempfile
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from chatdocs.adapters.http.auth import client_ip, container_of, current_auth, current_user
from chatdocs.adapters.http.schemas import CamelModel
from chatdocs.adapters.xlsx import testset_xlsx
from chatdocs.application.access_service import AuthContext
from chatdocs.domain.access.user import User
from chatdocs.domain.errors import RouteNotFound, TestsetInvalid

router = APIRouter(prefix="/api/v1", dependencies=[Depends(current_auth)], tags=["insights"])

MAX_XLSX_BYTES = 5 * 1024 * 1024
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class EventBody(CamelModel):
    name: str
    props: dict[str, Any] = {}


@router.post("/events", status_code=202)
async def track_event(request: Request, body: EventBody, auth: AuthContext = Depends(current_auth)) -> Response:
    container_of(request).analytics.ingest_frontend(auth, body.name, body.props)
    return Response(status_code=202)


@router.get("/metrics/weekly")
async def weekly_metrics(
    request: Request, weeks: int = Query(default=4, ge=1, le=12), user: User = Depends(current_user)
) -> list[dict]:
    rows = await container_of(request).metrics.weekly(user, weeks)
    return [
        {
            "week": m.week,
            "weekStart": m.week_start.isoformat(),
            "activeUsers": m.active_users,
            "wauRate": m.wau_rate,
            "questions": m.questions,
            "notFoundRate": m.not_found_rate,
            "helpfulRate": m.helpful_rate,
            "p95LatencyMs": m.p95_latency_ms,
        }
        for m in rows
    ]


def _run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise RouteNotFound() from None


def _evaluation(request: Request):
    c = container_of(request)
    if "evaluation" not in c.settings.flags:  # P2 behind a flag (dev_tasks.md Phần 6)
        raise RouteNotFound()
    return c.evaluation


@router.post("/evaluations", status_code=202)
async def start_evaluation(
    request: Request, file: UploadFile = File(...), auth: AuthContext = Depends(current_auth)
) -> dict:
    svc = _evaluation(request)
    data = await file.read(MAX_XLSX_BYTES + 1)
    if len(data) > MAX_XLSX_BYTES or not data:
        raise TestsetInvalid(row=1, column="file")
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        rows = testset_xlsx.read_rows(path)
    finally:
        os.unlink(path)
    run = await svc.start(auth, file.filename or "test-set.xlsx", rows, client_ip(request))
    return {"runId": str(run.run_id), "total": run.total}


@router.get("/evaluations/{run_id}")
async def evaluation_status(request: Request, run_id: str, user: User = Depends(current_user)) -> dict:
    st = await _evaluation(request).status(user, _run_id(run_id))
    return {"runId": str(st.run_id), "status": st.status, "done": st.done, "total": st.total}


@router.get("/evaluations/{run_id}/export")
async def evaluation_export(request: Request, run_id: str, user: User = Depends(current_user)) -> Response:
    results = await _evaluation(request).results(user, _run_id(run_id))
    return Response(
        testset_xlsx.build_results(results),
        media_type=XLSX_TYPE,
        headers={"Content-Disposition": f'attachment; filename="ket-qua-danh-gia-{run_id[:8]}.xlsx"'},
    )


@router.get("/evaluations-template")
async def evaluation_template(request: Request) -> Response:
    _evaluation(request)
    return Response(
        testset_xlsx.template(),
        media_type=XLSX_TYPE,
        headers={"Content-Disposition": 'attachment; filename="mau-bo-cau-hoi.xlsx"'},
    )
