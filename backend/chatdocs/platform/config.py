"""All tunables live here (dev_tasks.md §0.2). Values marked [Đề xuất] in the SAD must not be hard-coded elsewhere."""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Seeded by migration 0001 (PD-01: one shared library for the whole BD team).
DEFAULT_LIBRARY_ID = UUID("01920000-0000-7000-8000-000000000001")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    environment: str = "dev"
    app_secret: str = Field(default="dev-only-change-me", min_length=16)
    public_base_url: str = "http://localhost:5173"
    cookie_secure: bool = True
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://chatdocs:chatdocs@localhost:5432/chatdocs"
    library_id: UUID = DEFAULT_LIBRARY_ID

    s3_endpoint: str | None = "http://localhost:9000"
    s3_bucket: str = "chat-docs"
    s3_region: str = "ap-southeast-1"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_sse: str | None = "AES256"  # "aws:kms" on AWS; AES256 = SSE-S3 (MinIO)

    oidc_issuer: str = "http://localhost:8080/realms/chatdocs"
    oidc_internal_base_url: str | None = None  # e.g. http://keycloak:8080 inside docker compose
    oidc_client_id: str = "chatdocs"
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str = "http://localhost:5173/auth/callback"
    oidc_groups_claim: str = "groups"
    role_group_member: str = "grp-bd-member"
    role_group_lead: str = "grp-bd-lead"
    role_group_manager: str = "grp-bd-manager"
    session_idle_hours: int = 8

    max_upload_mb: int = 50

    embedder_url: str = "http://localhost:8081"
    embed_dim: int = 1024
    embed_batch: int = 32
    chunk_tokens: int = 500
    chunk_overlap: int = 80
    no_text_chars_per_page: int = 20

    retr_topk_vector: int = 30
    retr_topk_fts: int = 30
    retr_topn: int = 8
    retr_max_per_doc: int = 3
    retr_tau: float = 0.35
    rrf_k: int = 60
    hnsw_ef_search: int = 80

    worker_poll_seconds: float = 5.0
    worker_metrics_port: int | None = 9101  # Prometheus scrape port of the worker (None = off)

    # EN-06 — "fake" needs no key (dev / CI E2E); "anthropic" (Claude API); "openai_compatible" (vLLM / TGI, OQ-008)
    llm_provider: str = "fake"
    llm_model: str = "claude-sonnet-5-5"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_effort: str = "low"
    llm_refusal_fallback: bool = True
    llm_connect_timeout_s: float = 3
    llm_first_token_timeout_s: float = 10
    llm_total_timeout_s: float = 28
    llm_max_concurrency: int = 5  # per replica; 2 replicas × 5 = 10 (T-EN06.7)
    llm_queue_max: int = 20
    llm_queue_wait_s: float = 5
    llm_max_output_tokens: int = 800
    llm_context_tokens: int = 6000
    cb_failure_ratio: float = 0.5
    cb_min_calls: int = 10
    cb_window_s: float = 60
    cb_consecutive: int = 5
    cb_open_s: float = 30

    # EN-09
    rate_questions_per_min: int = 10
    rate_uploads_per_hour: int = 30
    rate_events_per_min: int = 60

    # EN-08
    analytics_hmac_key: str = Field(default="dev-only-analytics-key", min_length=16)

    # US-204
    purge_deadline_hours: int = 24

    # P1 / P2 behind flags: followup, history, duplicate, evaluation, stream_render
    feature_flags: str = "history,duplicate,stream_render"

    @property
    def flags(self) -> frozenset[str]:
        return frozenset(f.strip() for f in self.feature_flags.split(",") if f.strip())

    @property
    def cookie_names(self) -> tuple[str, str, str]:
        """(session, csrf, oidc-temp). The __Host- prefix needs Secure cookies; plain names for http dev setups."""
        p = "__Host-" if self.cookie_secure else ""
        return f"{p}session", f"{p}csrf", f"{p}oidc"


@lru_cache
def get_settings() -> Settings:
    return Settings()
