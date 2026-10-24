"""/auth/* — OIDC Authorization Code + PKCE handled by the backend (BFF, ADR-10). US-101, US-102, US-103."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from chatdocs.adapters.http.auth import CSRF_HEADER, client_ip, container_of
from chatdocs.domain.errors import CsrfInvalid, ForbiddenRole, IdentityProviderError
from chatdocs.platform.logging import get_logger
from chatdocs.platform.security import csrf_valid, safe_return_to, sign, unsign

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger("chatdocs.auth")

LOGIN_STATE_TTL = 600  # seconds the user has to complete the IdP login
SESSION_COOKIE_MAX_AGE = 14 * 3600  # covers a working day; the 8 h idle limit is enforced server-side


def _cookie_kwargs(request: Request, http_only: bool = True) -> dict:
    secure = container_of(request).settings.cookie_secure
    return {"httponly": http_only, "secure": secure, "samesite": "lax", "path": "/"}


@router.get("/login")
async def login(request: Request, returnTo: str | None = None):  # noqa: N803 — query name is part of the API
    c = container_of(request)
    _, _, oidc_cookie = c.settings.cookie_names
    try:
        start = await c.access.begin_login(returnTo)
    except IdentityProviderError:
        return RedirectResponse("/login?error=idp", status_code=302)
    temp = sign(
        {"s": start.state, "n": start.nonce, "v": start.code_verifier, "r": start.return_to},
        c.settings.app_secret,
        LOGIN_STATE_TTL,
    )
    resp = RedirectResponse(start.authorization_url, status_code=302)
    resp.set_cookie(oidc_cookie, temp, max_age=LOGIN_STATE_TTL, **_cookie_kwargs(request))
    return resp


@router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    c = container_of(request)
    session_cookie, csrf_cookie, oidc_cookie = c.settings.cookie_names
    temp = unsign(request.cookies.get(oidc_cookie), c.settings.app_secret)

    def fail(reason: str) -> RedirectResponse:
        resp = RedirectResponse(f"/login?error={quote(reason)}", status_code=302)
        resp.delete_cookie(oidc_cookie, path="/")
        return resp

    if error:
        return fail("idp")
    if not temp or not code or not state or state != temp.get("s"):
        log.warning("oidc_state_mismatch")
        return fail("state")
    try:
        result = await c.access.complete_login(
            code=code, code_verifier=temp["v"], nonce=temp["n"], ip=client_ip(request)
        )
    except ForbiddenRole:
        resp = RedirectResponse("/denied", status_code=302)
        resp.delete_cookie(oidc_cookie, path="/")
        return resp
    except IdentityProviderError:
        return fail("idp")

    resp = RedirectResponse(safe_return_to(temp.get("r")), status_code=302)
    resp.delete_cookie(oidc_cookie, path="/")
    resp.set_cookie(session_cookie, result.session_token, max_age=SESSION_COOKIE_MAX_AGE, **_cookie_kwargs(request))
    # Readable by JS on purpose: the SPA copies it into the X-CSRF-Token header.
    resp.set_cookie(
        csrf_cookie, result.csrf_token, max_age=SESSION_COOKIE_MAX_AGE, **_cookie_kwargs(request, http_only=False)
    )
    return resp


@router.post("/logout", status_code=204)
async def logout(request: Request) -> Response:
    c = container_of(request)
    session_cookie, csrf_cookie, _ = c.settings.cookie_names
    token = request.cookies.get(session_cookie)
    if token:
        # Logout changes state, so it needs the CSRF token too (otherwise any site could log users out).
        secret = await c.access.csrf_secret_of(token)
        if secret and not csrf_valid(secret, request.headers.get(CSRF_HEADER), request.cookies.get(csrf_cookie)):
            raise CsrfInvalid()
        await c.access.logout(token, client_ip(request))
    resp = Response(status_code=204)
    resp.delete_cookie(session_cookie, path="/")
    resp.delete_cookie(csrf_cookie, path="/")
    return resp
