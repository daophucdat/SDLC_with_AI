"""Authentication dependency: every /api/v1 route requires a valid session (default deny, T102.3) and a valid
CSRF token on unsafe methods (double-submit cookie bound to the session secret)."""

from __future__ import annotations

from fastapi import Request

from chatdocs.application.access_service import AuthContext
from chatdocs.domain.access.user import User
from chatdocs.domain.errors import CsrfInvalid
from chatdocs.platform.security import csrf_valid

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER = "X-CSRF-Token"


def container_of(request: Request):
    return request.app.state.container


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def current_auth(request: Request) -> AuthContext:
    cached = getattr(request.state, "auth", None)
    if cached is not None:
        return cached
    c = container_of(request)
    session_cookie, csrf_cookie, _ = c.settings.cookie_names
    ctx = await c.access.authenticate(request.cookies.get(session_cookie))
    if request.method in UNSAFE_METHODS and not csrf_valid(
        ctx.csrf_secret, request.headers.get(CSRF_HEADER), request.cookies.get(csrf_cookie)
    ):
        raise CsrfInvalid()
    request.state.auth = ctx
    return ctx


async def current_user(request: Request) -> User:
    return (await current_auth(request)).user
