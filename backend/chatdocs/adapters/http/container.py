"""Wires ports to concrete adapters. Tests build a Container from in-memory fakes instead."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from chatdocs.application.access_service import AccessService
from chatdocs.application.analytics_service import AnalyticsService
from chatdocs.application.document_service import DocumentService
from chatdocs.application.insights_service import EvaluationService, MetricsService
from chatdocs.application.qa_service import LlmGate, QaConfig, QuestionAnsweringService
from chatdocs.application.retrieval_service import RetrievalConfig, RetrievalService
from chatdocs.domain.access.role_mapping import RoleGroups
from chatdocs.domain.documents.upload_policy import UploadPolicy
from chatdocs.platform import metrics
from chatdocs.platform.circuit_breaker import CircuitBreaker
from chatdocs.platform.config import Settings
from chatdocs.platform.rate_limit import RateLimiter
from chatdocs.ports.clock import Clock, SystemClock

HealthCheck = Callable[[], Awaitable[bool]]


@dataclass
class Container:
    settings: Settings
    access: AccessService
    documents: DocumentService
    upload_policy: UploadPolicy
    clock: Clock = field(default_factory=SystemClock)
    qa: QuestionAnsweringService | None = None
    analytics: AnalyticsService | None = None
    metrics: MetricsService | None = None
    evaluation: EvaluationService | None = None
    health_checks: dict[str, HealthCheck] = field(default_factory=dict)
    starters: list[Callable[[], Awaitable[None]]] = field(default_factory=list)
    closers: list[Callable[[], Awaitable[None]]] = field(default_factory=list)


def role_groups(settings: Settings) -> RoleGroups:
    return RoleGroups(
        member=settings.role_group_member, lead=settings.role_group_lead, manager=settings.role_group_manager
    )


def retrieval_config(s: Settings) -> RetrievalConfig:
    return RetrievalConfig(
        topk_vector=s.retr_topk_vector,
        topk_fts=s.retr_topk_fts,
        top_n=s.retr_topn,
        max_per_document=s.retr_max_per_doc,
        tau=s.retr_tau,
        rrf_k=s.rrf_k,
    )


def qa_config(s: Settings) -> QaConfig:
    return QaConfig(
        context_tokens=s.llm_context_tokens,
        max_concurrency=s.llm_max_concurrency,
        queue_max=s.llm_queue_max,
        queue_wait_s=s.llm_queue_wait_s,
        followup_enabled="followup" in s.flags,
        history_enabled="history" in s.flags,
        qa_off="qa_off" in s.flags,
    )


def make_gate(s: Settings) -> LlmGate:
    breaker = CircuitBreaker(
        failure_ratio=s.cb_failure_ratio,
        min_calls=s.cb_min_calls,
        window_seconds=s.cb_window_s,
        consecutive=s.cb_consecutive,
        open_seconds=s.cb_open_s,
        on_state=lambda st: metrics.LLM_CIRCUIT.set(metrics.CIRCUIT_VALUE[st.value]),
    )
    return LlmGate(breaker, s.llm_max_concurrency, s.llm_queue_max, s.llm_queue_wait_s)


def make_llm(s: Settings):
    """Provider adapter wrapped with the timeout / retry policy (EN-06)."""
    from chatdocs.adapters.llm.resilient import ResilientGenerator

    if s.llm_provider == "anthropic":
        from chatdocs.adapters.llm.anthropic_adapter import AnthropicAnswerGenerator

        inner = AnthropicAnswerGenerator(
            model=s.llm_model,
            api_key=s.llm_api_key,
            base_url=s.llm_base_url,
            max_output_tokens=s.llm_max_output_tokens,
            connect_timeout_s=s.llm_connect_timeout_s,
            read_timeout_s=s.llm_total_timeout_s,
            effort=s.llm_effort,
            refusal_fallback=s.llm_refusal_fallback,
        )
    elif s.llm_provider == "openai_compatible":
        from chatdocs.adapters.llm.openai_compatible import OpenAICompatibleGenerator

        if not s.llm_base_url:
            raise ValueError("LLM_BASE_URL is required for LLM_PROVIDER=openai_compatible")
        inner = OpenAICompatibleGenerator(
            base_url=s.llm_base_url,
            model=s.llm_model,
            api_key=s.llm_api_key,
            max_output_tokens=s.llm_max_output_tokens,
            connect_timeout_s=s.llm_connect_timeout_s,
            read_timeout_s=s.llm_total_timeout_s,
        )
    elif s.llm_provider == "fake":
        if s.environment == "prod":
            raise ValueError("LLM_PROVIDER=fake is not allowed in prod")
        from chatdocs.adapters.llm.fake import FakeAnswerGenerator

        inner = FakeAnswerGenerator()
    else:
        raise ValueError(f"unknown LLM_PROVIDER {s.llm_provider!r}")
    return ResilientGenerator(
        inner, first_token_timeout_s=s.llm_first_token_timeout_s, total_timeout_s=s.llm_total_timeout_s
    )


async def build_container(settings: Settings) -> Container:
    # Imported here so unit tests that pass their own container never need database / AWS libraries configured.
    from chatdocs.adapters.analytics.postgres_sink import PostgresEventWriter
    from chatdocs.adapters.db.insights_repository import PgEvaluationRepository, PgMetricsRepository
    from chatdocs.adapters.db.qa_repository import PgQaRepository, PgStopBus
    from chatdocs.adapters.db.repositories import (
        PgAuditLog,
        PgDocumentRepository,
        PgJobQueue,
        PgSessionRepository,
        PgUserRepository,
        db_health,
        make_engine,
    )
    from chatdocs.adapters.embedder.tei import TeiEmbedder
    from chatdocs.adapters.oidc.generic import OidcProvider
    from chatdocs.adapters.pgvector.chunk_index import PgVectorChunkIndex
    from chatdocs.adapters.storage.s3 import S3DocumentStorage

    s = settings
    engine = make_engine(s.database_url)
    clock = SystemClock()
    audit = PgAuditLog(engine)
    storage = S3DocumentStorage(
        bucket=s.s3_bucket,
        endpoint=s.s3_endpoint,
        region=s.s3_region,
        access_key=s.s3_access_key,
        secret_key=s.s3_secret_key,
        sse=s.s3_sse,
    )
    embedder = TeiEmbedder(base_url=s.embedder_url, dimension=s.embed_dim, batch_size=s.embed_batch)
    writer = PostgresEventWriter(engine)
    analytics = AnalyticsService(
        writer=writer,
        hmac_key=s.analytics_hmac_key.encode(),
        app_version=s.app_version,
        clock=clock,
        rate_limiter=RateLimiter(capacity=s.rate_events_per_min, per_seconds=60),
    )
    policy = UploadPolicy(s.max_upload_mb)
    access = AccessService(
        idp=OidcProvider(
            issuer=s.oidc_issuer,
            client_id=s.oidc_client_id,
            client_secret=s.oidc_client_secret,
            groups_claim=s.oidc_groups_claim,
            internal_base_url=s.oidc_internal_base_url,
        ),
        users=PgUserRepository(engine),
        sessions=PgSessionRepository(engine),
        audit=audit,
        role_groups=role_groups(s),
        idle_hours=s.session_idle_hours,
        redirect_uri=s.oidc_redirect_uri,
        clock=clock,
        analytics=analytics,
    )
    doc_repo = PgDocumentRepository(engine)
    documents = DocumentService(
        documents=doc_repo,
        storage=storage,
        audit=audit,
        policy=policy,
        library_id=s.library_id,
        clock=clock,
        analytics=analytics,
        upload_limiter=RateLimiter(capacity=s.rate_uploads_per_hour, per_seconds=3600),
    )
    stop_bus = PgStopBus(engine)
    qa = QuestionAnsweringService(
        qa=PgQaRepository(engine),
        documents=doc_repo,
        retrieval=RetrievalService(
            embedder=embedder,
            index=PgVectorChunkIndex(engine, ef_search=s.hnsw_ef_search),
            config=retrieval_config(s),
        ),
        llm=make_llm(s),
        gate=make_gate(s),
        analytics=analytics,
        stop_bus=stop_bus,
        rate_limiter=RateLimiter(capacity=s.rate_questions_per_min, per_seconds=60),
        library_id=s.library_id,
        clock=clock,
        config=qa_config(s),
    )
    return Container(
        settings=s,
        access=access,
        documents=documents,
        upload_policy=policy,
        clock=clock,
        qa=qa,
        analytics=analytics,
        metrics=MetricsService(repo=PgMetricsRepository(engine), clock=clock),
        # The API only creates runs and reads results; the worker executes them (it gets its own Q&A service).
        evaluation=EvaluationService(
            repo=PgEvaluationRepository(engine), jobs=PgJobQueue(engine), qa=None, audit=audit, clock=clock
        ),
        # The LLM is deliberately not a readiness dependency (SAD §4.3):
        # an AI outage must not pull the API out of the load balancer.
        health_checks={"database": lambda: db_health(engine), "storage": storage.health, "embedder": embedder.health},
        starters=[writer.start, stop_bus.start],
        closers=[stop_bus.close, writer.close, engine.dispose],
    )
