"""Analytics (EN-08). Every event — from the server or the browser — passes the allow-list (domain.analytics.events)
and leaves this module with a keyed hash instead of the user id (`user_id_hash = HMAC_SHA256(key, user_id)`)."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from chatdocs.application.access_service import AuthContext
from chatdocs.domain.analytics.events import FRONTEND_EVENTS, validate_event
from chatdocs.domain.errors import EventInvalid, RateLimited
from chatdocs.platform import metrics
from chatdocs.platform.logging import get_logger
from chatdocs.platform.rate_limit import RateLimiter, seconds
from chatdocs.ports.clock import Clock

log = get_logger("chatdocs.analytics")


@dataclass(frozen=True)
class EventRecord:
    name: str
    ts: datetime
    user_id_hash: str
    session_id: str | None
    app_version: str
    props: dict[str, Any]


class EventWriter(Protocol):
    def submit(self, record: EventRecord) -> bool:
        """Non-blocking hand-off to the batching writer. False if the buffer is full (event dropped)."""
        ...


def user_hash(key: bytes, user_id: UUID) -> str:
    return hmac.new(key, str(user_id).encode(), hashlib.sha256).hexdigest()


class AnalyticsService:
    """Implements the AnalyticsSink port for the server side and the POST /events use case for the browser."""

    def __init__(
        self, *, writer: EventWriter, hmac_key: bytes, app_version: str, clock: Clock, rate_limiter: RateLimiter
    ) -> None:
        self._writer, self._key, self._version = writer, hmac_key, app_version
        self._clock, self._rate = clock, rate_limiter

    def emit(self, name: str, props: dict[str, Any], *, user_id: UUID | None, session_id: str | None) -> None:
        try:
            props = validate_event(name, props)
        except EventInvalid as e:
            # A server-side event that fails the allow-list is a bug: log the field name, never the value.
            log.error("analytics_event_rejected", event_name=name, field=e.details.get("field"))
            return
        record = EventRecord(
            name=name,
            ts=self._clock.now(),
            user_id_hash=user_hash(self._key, user_id) if user_id else "anonymous",
            session_id=session_id,
            app_version=self._version,
            props=props,
        )
        if not self._writer.submit(record):
            metrics.ANALYTICS_DROPPED.inc()

    def ingest_frontend(self, auth: AuthContext, name: str, props: dict[str, Any] | None) -> None:
        if name not in FRONTEND_EVENTS:
            raise EventInvalid(field="name")
        wait = self._rate.acquire(f"ev:{auth.user.id}")
        if wait:
            raise RateLimited(retryAfter=seconds(wait))
        validate_event(name, props)  # raises EVENT_INVALID (400) for the browser
        self.emit(name, props or {}, user_id=auth.user.id, session_id=auth.session_id_hash.hex()[:16])
