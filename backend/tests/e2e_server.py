"""E2E test server (Day 6, docs/test-plan.md §5): the real FastAPI app, real PDF processing (PyMuPDF), in-memory
storage / index / repositories, the scripted fake LLM, and a test identity provider. No Docker, PostgreSQL, MinIO,
TEI or Keycloak needed, so Playwright can run every test case on a laptop and in CI in a few minutes.

    cd backend && .venv/Scripts/python -m tests.e2e_server   # API :8000, Vite :5180 (playwright.config.ts)

TEST ONLY — lives under tests/, is never packaged (the Dockerfile copies chatdocs/ only) and refuses to start when
ENVIRONMENT=prod. The full-stack run (Keycloak, PostgreSQL, MinIO, TEI) is the CI job `e2e` on docker compose."""

from __future__ import annotations

import asyncio
import html
import os
from urllib.parse import urlencode

import uvicorn
from fastapi import Request
from fastapi.responses import HTMLResponse

from chatdocs.adapters.http.main import create_app
from chatdocs.adapters.jobs.runner import JobRunner, document_id_of
from chatdocs.adapters.pdf.pymupdf_extractor import PyMuPdfExtractor
from chatdocs.application.document_processing_service import DocumentProcessingService, ProcessingConfig
from chatdocs.domain.jobs import JobType
from chatdocs.ports.clock import SystemClock
from tests.fakes import FakeIdp, make_container

API_PORT = int(os.environ.get("E2E_API_PORT", "8000"))
WEB_BASE = os.environ.get("E2E_WEB_BASE", "http://localhost:5180")
IDP_BASE = os.environ.get("E2E_IDP_BASE", f"http://localhost:{API_PORT}")
TEST_USERS = ("member", "member2", "lead", "manager", "outsider", "broken")


class TestIdp(FakeIdp):
    """Login page with one link per test account instead of a real IdP form (OIDC code + state + nonce kept)."""

    __test__ = False

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        await super().authorization_url(
            state=state, nonce=nonce, code_challenge=code_challenge, redirect_uri=redirect_uri
        )
        return f"{IDP_BASE}/__test-idp?{urlencode({'state': state})}"


def login_page(state: str) -> str:
    links = "".join(
        f'<li><a id="login-{u}" href="{html.escape(WEB_BASE)}/auth/callback?{urlencode({"code": u, "state": state})}">'
        f"{u}</a></li>"
        for u in TEST_USERS
    )
    return f"<!doctype html><html lang='vi'><title>Test IdP</title><h1>Test IdP (E2E)</h1><ul>{links}</ul></html>"


def build_app():
    if os.environ.get("ENVIRONMENT") == "prod":
        raise SystemExit("tests.e2e_server must never run in prod")
    container, f = make_container(
        clock=SystemClock(),
        cookie_secure=False,  # plain http on localhost
        public_base_url=WEB_BASE,
        oidc_redirect_uri=f"{WEB_BASE}/auth/callback",
        max_upload_mb=50,  # the real limit (US-201): boundary test cases depend on it
        feature_flags="history,duplicate,stream_render,followup",
        rate_uploads_per_hour=500,  # test runs upload many files; the limit itself is covered by API tests
        rate_questions_per_min=200,
        llm_first_token_timeout_s=10,
        llm_total_timeout_s=28,
        log_level="WARNING",
    )
    f.idp.__class__ = TestIdp
    f.llm._delay = 0.02  # visible streaming, still fast
    processing = DocumentProcessingService(
        documents=f.documents,
        storage=f.storage,
        extractor=PyMuPdfExtractor(),
        embedder=f.embedder,
        index=f.index,
        config=ProcessingConfig(),
        analytics=f.analytics,
    )

    async def process(job) -> None:
        await processing.process(document_id_of(job))

    runner = JobRunner(
        queue=f.jobs, clock=SystemClock(), handlers={JobType.PROCESS_DOCUMENT: process}, poll_seconds=0.3
    )

    async def start_worker() -> None:
        asyncio.get_running_loop().create_task(runner.serve())

    async def stop_worker() -> None:
        runner.stop()

    container.starters.append(start_worker)
    container.closers.append(stop_worker)
    app = create_app(container)

    @app.get("/__test-idp", include_in_schema=False)
    async def test_idp(request: Request) -> HTMLResponse:
        return HTMLResponse(login_page(request.query_params.get("state", "")))

    return app


if __name__ == "__main__":
    uvicorn.run(build_app(), host="127.0.0.1", port=API_PORT, log_level="warning")
