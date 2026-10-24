"""FastAPI application factory. Run: `uvicorn chatdocs.adapters.http.main:app`."""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from chatdocs.adapters.http import problem
from chatdocs.adapters.http.container import Container, build_container
from chatdocs.adapters.http.routes_api import fallback_router
from chatdocs.adapters.http.routes_api import router as api_router
from chatdocs.adapters.http.routes_auth import router as auth_router
from chatdocs.adapters.http.routes_insights import router as insights_router
from chatdocs.adapters.http.routes_qa import router as qa_router
from chatdocs.domain.errors import DomainError
from chatdocs.platform import metrics
from chatdocs.platform.config import Settings, get_settings
from chatdocs.platform.logging import configure_logging, get_logger
from chatdocs.platform.tracing import configure_tracing

log = get_logger("chatdocs.http")
PUBLIC_PATHS = ("/auth/", "/healthz", "/readyz", "/metrics")  # everything else is behind current_auth

# T-EN09.2. The SPA is served by the reverse proxy with the same policy (infra/nginx/chatdocs.conf).
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; worker-src 'self' blob:; img-src 'self' data: blob:; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
}


def create_app(container: Container | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or (container.settings if container else get_settings())
    configure_logging(settings.log_level)
    configure_tracing("chatdocs-api", settings.app_version)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if getattr(app.state, "container", None) is None:
            app.state.container = await build_container(settings)
        for start in app.state.container.starters:
            await start()
        yield
        for close in app.state.container.closers:
            await close()

    app = FastAPI(
        title="Chat với tài liệu API",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.environment == "dev" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.environment == "dev" else None,
    )
    app.state.container = container

    @app.middleware("http")
    async def trace_and_access_log(request: Request, call_next):
        parts = request.headers.get("traceparent", "").split("-")  # W3C: version-traceid-spanid-flags
        request.state.trace_id = parts[1] if len(parts) == 4 and len(parts[1]) == 32 else uuid.uuid4().hex
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Trace-Id"] = request.state.trace_id
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        # Route template, not the raw path: ids must not become metric labels.
        route = getattr(request.scope.get("route"), "path", "unmatched")
        metrics.HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
        metrics.HTTP_LATENCY.labels(route).observe(time.perf_counter() - t0)
        # Access log without query string or body: questions and file names must not reach logs (TC-08).
        log.info(
            "http_request",
            method=request.method,
            route=route,
            status=response.status_code,
            trace_id=request.state.trace_id,
        )
        return response

    app.add_exception_handler(DomainError, problem.domain_error_handler)
    app.add_exception_handler(RequestValidationError, problem.validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, problem.http_error_handler)
    app.add_exception_handler(Exception, problem.unhandled_error_handler)

    app.include_router(auth_router)
    app.include_router(api_router)
    app.include_router(qa_router)
    app.include_router(insights_router)
    app.include_router(fallback_router)  # must stay last

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> JSONResponse:
        checks = request.app.state.container.health_checks
        results = await asyncio.gather(*(check() for check in checks.values()), return_exceptions=True)
        status = {name: (r is True) for name, r in zip(checks, results, strict=True)}
        ok = all(status.values())
        return JSONResponse({"status": "ok" if ok else "degraded", "checks": status}, status_code=200 if ok else 503)

    @app.get("/metrics", include_in_schema=False)
    async def prometheus() -> Response:
        # Scraped on the internal network only; the reverse proxy does not route /metrics (infra/nginx).
        return Response(metrics.render(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
