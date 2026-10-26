"""Worker process: `python -m chatdocs.adapters.jobs.worker_main`. Document processing, purges, scheduled housekeeping
and evaluation runs happen here, never in the API (ADR-05)."""

from __future__ import annotations

import asyncio
import contextlib
import signal
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from prometheus_client import start_http_server
from sqlalchemy.ext.asyncio import AsyncEngine

from chatdocs.adapters.analytics.postgres_sink import PostgresEventWriter
from chatdocs.adapters.db.insights_repository import PgEvaluationRepository, PgMetricsRepository
from chatdocs.adapters.db.qa_repository import LocalStopBus, PgQaRepository
from chatdocs.adapters.db.repositories import (
    PgAuditLog,
    PgDocumentRepository,
    PgJobQueue,
    PgSessionRepository,
    make_engine,
)
from chatdocs.adapters.embedder.tei import TeiEmbedder
from chatdocs.adapters.http.container import make_gate, make_llm, qa_config, retrieval_config
from chatdocs.adapters.jobs.runner import JobRunner, document_id_of
from chatdocs.adapters.pdf.pymupdf_extractor import PyMuPdfExtractor
from chatdocs.adapters.pgvector.chunk_index import PgVectorChunkIndex
from chatdocs.adapters.storage.s3 import S3DocumentStorage
from chatdocs.application.analytics_service import AnalyticsService
from chatdocs.application.document_processing_service import DocumentProcessingService, ProcessingConfig
from chatdocs.application.document_service import DocumentService
from chatdocs.application.insights_service import EvaluationService, MetricsService
from chatdocs.application.maintenance import enqueue_due
from chatdocs.application.qa_service import QuestionAnsweringService
from chatdocs.application.retrieval_service import RetrievalService
from chatdocs.domain.documents.upload_policy import UploadPolicy
from chatdocs.domain.jobs import JobType
from chatdocs.platform import metrics
from chatdocs.platform.config import Settings, get_settings
from chatdocs.platform.logging import configure_logging, get_logger
from chatdocs.platform.rate_limit import RateLimiter
from chatdocs.platform.tracing import configure_tracing
from chatdocs.ports.clock import Clock, SystemClock

log = get_logger("chatdocs.worker")
SCHEDULER_SECONDS = 60


def loop_time() -> float:
    return asyncio.get_running_loop().time()


@dataclass
class Worker:
    """Everything the worker runs, wired once from Settings (adapters → application services)."""

    settings: Settings
    engine: AsyncEngine
    clock: Clock
    queue: PgJobQueue
    writer: PostgresEventWriter
    processing: DocumentProcessingService
    documents: DocumentService
    sessions: PgSessionRepository
    metrics: MetricsService
    evaluation: EvaluationService


def build_worker(s: Settings) -> Worker:
    engine = make_engine(s.database_url)
    clock = SystemClock()
    queue = PgJobQueue(engine)
    repo = PgDocumentRepository(engine)
    storage = S3DocumentStorage(
        bucket=s.s3_bucket,
        endpoint=s.s3_endpoint,
        region=s.s3_region,
        access_key=s.s3_access_key,
        secret_key=s.s3_secret_key,
        sse=s.s3_sse,
    )
    embedder = TeiEmbedder(base_url=s.embedder_url, dimension=s.embed_dim, batch_size=s.embed_batch)
    index = PgVectorChunkIndex(engine, ef_search=s.hnsw_ef_search)
    writer = PostgresEventWriter(engine)
    analytics = AnalyticsService(
        writer=writer,
        hmac_key=s.analytics_hmac_key.encode(),
        app_version=s.app_version,
        clock=clock,
        rate_limiter=RateLimiter(capacity=10_000, per_seconds=60),
    )
    audit = PgAuditLog(engine)
    processing = DocumentProcessingService(
        documents=repo,
        storage=storage,
        extractor=PyMuPdfExtractor(),
        embedder=embedder,
        index=index,
        config=ProcessingConfig(
            chunk_tokens=s.chunk_tokens,
            chunk_overlap=s.chunk_overlap,
            no_text_chars_per_page=s.no_text_chars_per_page,
            embed_batch=s.embed_batch,
        ),
        analytics=analytics,
    )
    documents = DocumentService(
        documents=repo,
        storage=storage,
        audit=audit,
        policy=UploadPolicy(s.max_upload_mb),
        library_id=s.library_id,
        clock=clock,
        index=index,
    )
    qa = QuestionAnsweringService(  # used by evaluation runs only — same pipeline as the API (US-402)
        qa=PgQaRepository(engine),
        documents=repo,
        retrieval=RetrievalService(embedder=embedder, index=index, config=retrieval_config(s)),
        llm=make_llm(s),
        gate=make_gate(s),
        analytics=analytics,
        stop_bus=LocalStopBus(),
        rate_limiter=RateLimiter(capacity=10_000, per_seconds=60),
        library_id=s.library_id,
        clock=clock,
        config=qa_config(s),
    )
    return Worker(
        settings=s,
        engine=engine,
        clock=clock,
        queue=queue,
        writer=writer,
        processing=processing,
        documents=documents,
        sessions=PgSessionRepository(engine),
        metrics=MetricsService(repo=PgMetricsRepository(engine), clock=clock),
        evaluation=EvaluationService(repo=PgEvaluationRepository(engine), jobs=queue, qa=qa, audit=audit, clock=clock),
    )


class Handlers:
    """One method per job type (SAD §2.2)."""

    def __init__(self, w: Worker) -> None:
        self.w = w

    async def process(self, job) -> None:
        t0 = loop_time()
        result = await self.w.processing.process(document_id_of(job))
        metrics.DOCS_PROCESSED.labels(result.outcome.value).inc()
        metrics.DOC_PROCESSING.labels(result.outcome.value).observe(loop_time() - t0)
        log.info(
            "document_processed",
            document_id=str(document_id_of(job)),
            outcome=result.outcome.value,
            page_count=result.page_count,
            chunk_count=result.chunk_count,
        )

    async def give_up(self, job) -> None:
        await self.w.processing.give_up(document_id_of(job))

    async def purge(self, job) -> None:
        await self.w.documents.purge(document_id_of(job))
        log.info("document_purged", document_id=str(document_id_of(job)))  # also the input of REL-02 step 4

    async def purge_exhausted(self, job) -> None:
        log.error("document_purge_failed", document_id=str(document_id_of(job)))  # alert: SEC-06 at risk

    async def sweep(self, job) -> None:
        idle = timedelta(hours=self.w.settings.session_idle_hours)
        log.info("sessions_swept", count=await self.w.sessions.delete_idle(self.w.clock.now() - idle))

    async def rollup(self, job) -> None:
        values = await self.w.metrics.rollup()
        actions = await self.w.metrics.maintain_partitions()
        log.info("metrics_rolled_up", metric_count=len(values), partition_actions=len(actions))

    async def run_evaluation(self, job) -> None:
        outcome = await self.w.evaluation.execute(UUID(str(job.payload["run_id"])))
        log.info("evaluation_finished", run_id=str(job.payload["run_id"]), outcome=outcome)

    def runner(self) -> JobRunner:
        return JobRunner(
            queue=self.w.queue,
            clock=self.w.clock,
            poll_seconds=self.w.settings.worker_poll_seconds,
            handlers={
                JobType.PROCESS_DOCUMENT: self.process,
                JobType.PURGE_DOCUMENT: self.purge,
                JobType.SWEEP_SESSIONS: self.sweep,
                JobType.ROLLUP_METRICS: self.rollup,
                JobType.RUN_EVALUATION: self.run_evaluation,
            },
            on_exhausted={JobType.PROCESS_DOCUMENT: self.give_up, JobType.PURGE_DOCUMENT: self.purge_exhausted},
        )


async def scheduler_tick(w: Worker) -> None:
    await enqueue_due(w.queue, w.clock.now())
    metrics.PURGE_OVERDUE.set(await w.documents.purge_overdue())  # T204.3 → alert rule
    for job_type, (n, oldest) in (await w.queue.queued_stats()).items():
        metrics.JOB_QUEUE_DEPTH.labels(job_type).set(n)
        metrics.JOB_OLDEST_SECONDS.labels(job_type).set(oldest)


async def scheduler(w: Worker) -> None:
    while True:
        try:
            await scheduler_tick(w)
        except Exception as e:  # noqa: BLE001 — the scheduler must survive a DB blip
            log.warning("scheduler_tick_failed", error_type=type(e).__name__)
        await asyncio.sleep(SCHEDULER_SECONDS)


def install_signal_handlers(runner: JobRunner) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows dev machines
            loop.add_signal_handler(sig, runner.stop)


async def main() -> None:
    s = get_settings()
    configure_logging(s.log_level)
    configure_tracing("chatdocs-worker", s.app_version)
    if s.worker_metrics_port:
        start_http_server(s.worker_metrics_port, registry=metrics.REGISTRY)  # scraped as job chatdocs-worker
    w = build_worker(s)
    await w.writer.start()
    runner = Handlers(w).runner()

    # LISTEN jobs: wake up as soon as an upload commits instead of waiting for the next poll.
    listen_conn = await w.engine.connect()
    raw = await listen_conn.get_raw_connection()
    await raw.driver_connection.add_listener("jobs", runner.notify)
    install_signal_handlers(runner)
    log.info("worker_started", worker_id=runner.worker_id)
    sched = asyncio.create_task(scheduler(w))
    try:
        await runner.serve()
    finally:
        sched.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sched
        await w.writer.close()
        await listen_conn.close()
        await w.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
