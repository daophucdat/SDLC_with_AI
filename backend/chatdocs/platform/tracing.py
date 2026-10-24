"""Tracing (T-EN07.1). Uses OpenTelemetry when the SDK is installed and OTEL_EXPORTER_OTLP_ENDPOINT is set;
otherwise every span is a no-op, so code can always call `span(...)`. Span attributes are counts and durations
only — never question, answer or document text (TC-08)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

try:  # optional dependency: `pip install .[otel]`
    from opentelemetry import trace as _trace
except ImportError:  # pragma: no cover - exercised when the extra is not installed
    _trace = None

ALLOWED_ATTR_TYPES = (int, float, bool)
_tracer = _trace.get_tracer("chatdocs") if _trace else None


def configure_tracing(service_name: str, version: str) -> bool:
    """Installs the OTLP exporter. Returns True if tracing is active."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not (_trace and endpoint):
        return False
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return False
    provider = TracerProvider(resource=Resource.create({"service.name": service_name, "service.version": version}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    _trace.set_tracer_provider(provider)
    global _tracer
    _tracer = _trace.get_tracer("chatdocs")
    return True


@contextmanager
def span(name: str, **attributes: Any):
    """`with span("retrieve.vector", k=30): ...` — non-numeric attributes are dropped, not recorded."""
    if _tracer is None:
        yield None
        return
    safe = {k: v for k, v in attributes.items() if isinstance(v, ALLOWED_ATTR_TYPES)}
    # Not attached to the context: spans may wrap `yield` in async generators that resume in other tasks (SSE),
    # where detaching a context token fails. The parent is still the current (request) span.
    s = _tracer.start_span(name, attributes=safe)
    try:
        yield s
    finally:
        s.end()
