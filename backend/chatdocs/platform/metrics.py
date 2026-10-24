"""Prometheus metrics (T-EN07.2, SAD §4.3). Labels are bounded enums — never user ids, file names or text."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"], registry=REGISTRY)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP latency",
    ["route"],
    registry=REGISTRY,
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)
QA_LATENCY = Histogram(
    "qa_answer_latency_seconds",
    "Question → final event (NFR-01)",
    ["status"],
    registry=REGISTRY,
    buckets=(1, 2, 5, 8, 10, 15, 20, 30, 60),
)
QA_FIRST_TOKEN = Histogram(
    "qa_first_token_seconds",
    "Question → first delta (NFR-02)",
    registry=REGISTRY,
    buckets=(0.5, 1, 2, 3, 5, 8, 10, 20),
)
QA_ANSWERS = Counter("qa_answers_total", "Answers by final status", ["status", "reason"], registry=REGISTRY)
QA_NOT_FOUND = Counter("qa_not_found_total", "NOT_FOUND answers", ["reason"], registry=REGISTRY)
QA_CITATION_INVALID = Counter("qa_citation_invalid_total", "Answers rejected by ALG-3 (R-004)", registry=REGISTRY)
RETRIEVAL_LATENCY = Histogram(
    "retrieval_seconds", "Hybrid retrieval", registry=REGISTRY, buckets=(0.05, 0.1, 0.25, 0.5, 1, 2)
)
LLM_REQUESTS = Counter("llm_requests_total", "LLM calls", ["outcome"], registry=REGISTRY)
LLM_TOKENS = Counter("llm_tokens_total", "LLM tokens", ["direction"], registry=REGISTRY)
LLM_CIRCUIT = Gauge("llm_circuit_state", "0 closed, 1 half-open, 2 open", registry=REGISTRY)
LLM_QUEUE = Gauge("llm_queue_waiting", "Questions waiting for an LLM slot", registry=REGISTRY)
JOBS = Counter("jobs_total", "Background jobs", ["type", "outcome"], registry=REGISTRY)
JOB_FAILURES = Counter("job_failures_total", "Jobs that exhausted their retries", ["type"], registry=REGISTRY)
JOB_QUEUE_DEPTH = Gauge("job_queue_depth", "Queued jobs", ["type"], registry=REGISTRY)
JOB_OLDEST_SECONDS = Gauge("job_queue_oldest_seconds", "Age of the oldest queued job", ["type"], registry=REGISTRY)
DOC_PROCESSING = Histogram(
    "doc_processing_seconds",
    "Upload → READY / NO_TEXT / ERROR in the worker (NFR-03)",
    ["outcome"],
    registry=REGISTRY,
    buckets=(5, 15, 30, 60, 120, 180, 300, 600),
)
PURGE_OVERDUE = Gauge("documents_purge_overdue", "Removed > 20 h ago and still not purged (SEC-06)", registry=REGISTRY)
DOCS_PROCESSED = Counter("documents_processed_total", "Processing outcomes", ["outcome"], registry=REGISTRY)
ANALYTICS_DROPPED = Counter("analytics_events_dropped_total", "Events lost (buffer full / DB error)", registry=REGISTRY)

CIRCUIT_VALUE = {"closed": 0, "half_open": 1, "open": 2}


def render() -> bytes:
    return generate_latest(REGISTRY)
