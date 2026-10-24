"""Q1 → Q5 (US-301 → US-311). The answer is a Server-Sent Events stream (dev_tasks.md §0.5)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import Field

from chatdocs.adapters.http.auth import container_of, current_auth
from chatdocs.adapters.http.schemas import CamelModel
from chatdocs.application.access_service import AuthContext
from chatdocs.application.qa_service import citation_dto
from chatdocs.domain.errors import RouteNotFound

router = APIRouter(prefix="/api/v1", dependencies=[Depends(current_auth)], tags=["qa"])

PING_SECONDS = 15.0
SSE_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


class AskBody(CamelModel):
    text: str = ""
    follow_up: bool = False
    is_suggested: bool = False


class FeedbackBody(CamelModel):
    value: str
    reason: str | None = Field(default=None)


def _id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise RouteNotFound() from None


def _qa(request: Request):
    qa = container_of(request).qa
    if qa is None:  # pragma: no cover - misconfiguration
        raise RouteNotFound()
    return qa


def format_event(name: str, data: dict[str, Any]) -> bytes:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


async def sse(events: AsyncIterator[tuple[str, dict[str, Any]]], ping_seconds: float = PING_SECONDS):
    """Serialises events and inserts `: ping` comments while the producer is quiet, so proxies keep the connection."""
    it = events.__aiter__()
    pending: asyncio.Future | None = asyncio.ensure_future(it.__anext__())
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=ping_seconds)
            if not done:
                yield b": ping\n\n"
                continue
            try:
                name, data = pending.result()
            except StopAsyncIteration:
                pending = None
                return
            yield format_event(name, data)
            pending = asyncio.ensure_future(it.__anext__())
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, StopAsyncIteration, Exception):  # noqa: BLE001, S110 — already closing
                pass
        await it.aclose()  # runs the producer's finally: releases the LLM slot, records a disconnect


@router.post("/conversations", status_code=201)
async def create_conversation(request: Request, auth: AuthContext = Depends(current_auth)) -> dict:
    return {"id": str(await _qa(request).start_conversation(auth))}


@router.post("/conversations/{conversation_id}/questions")
async def ask(
    request: Request, conversation_id: str, body: AskBody, auth: AuthContext = Depends(current_auth)
) -> StreamingResponse:
    # prepare() raises 400 / 404 / 409 / 429 / 503 as problem+json before any byte of the stream is sent.
    handle = await _qa(request).prepare(
        auth, _id(conversation_id), body.text, follow_up=body.follow_up, is_suggested=body.is_suggested
    )
    return StreamingResponse(sse(handle.events()), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/conversations/{conversation_id}/questions")
async def history(request: Request, conversation_id: str, auth: AuthContext = Depends(current_auth)) -> list[dict]:
    """Q3 / US-308: only the session that owns the conversation can read it."""
    turns = await _qa(request).history(auth, _id(conversation_id))
    return [
        {
            "questionId": str(t.question_id),
            "text": t.question_text,
            "answer": {
                "answerId": str(t.answer_id),
                "text": t.answer_text,
                "status": t.status.value,
                "citations": [citation_dto(c) for c in t.citations],
                "feedback": t.feedback,
            },
        }
        for t in turns
    ]


@router.post("/answers/{answer_id}/stop", status_code=202)
async def stop(request: Request, answer_id: str, auth: AuthContext = Depends(current_auth)) -> Response:
    await _qa(request).stop(auth, _id(answer_id))
    return Response(status_code=202)


@router.post("/answers/{answer_id}/feedback", status_code=204)
async def feedback(
    request: Request, answer_id: str, body: FeedbackBody, auth: AuthContext = Depends(current_auth)
) -> Response:
    await _qa(request).feedback(auth, _id(answer_id), body.value, body.reason)
    return Response(status_code=204)
