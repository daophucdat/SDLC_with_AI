"""T102.5 / LG-10: unauthorised access must be refused in 100% of cases (≥ 20 cases)."""

from __future__ import annotations

import httpx
import pytest

from chatdocs.adapters.http.main import create_app
from tests.conftest import csrf_headers, login, pdf_bytes
from tests.fakes import make_container

UPLOAD = {"files": {"file": ("a.pdf", pdf_bytes(), "application/pdf")}}

ROUTES = [
    ("GET", "/api/v1/me", {}),
    ("GET", "/api/v1/documents", {}),
    ("GET", "/api/v1/documents?q=hop", {}),
    ("POST", "/api/v1/documents", UPLOAD),
    ("POST", "/api/v1/documents/00000000-0000-0000-0000-000000000000/retry", {}),
    ("DELETE", "/api/v1/documents/00000000-0000-0000-0000-000000000000", {}),
    ("GET", "/api/v1/documents/00000000-0000-0000-0000-000000000000/file", {}),
    ("POST", "/api/v1/conversations", {}),
    ("POST", "/api/v1/conversations/00000000-0000-0000-0000-000000000000/questions", {"json": {"text": "Giá?"}}),
    ("GET", "/api/v1/conversations/00000000-0000-0000-0000-000000000000/questions", {}),
    ("POST", "/api/v1/answers/00000000-0000-0000-0000-000000000000/stop", {}),
    ("POST", "/api/v1/answers/00000000-0000-0000-0000-000000000000/feedback", {"json": {"value": "HELPFUL"}}),
    ("POST", "/api/v1/events", {"json": {"name": "answer_copied", "props": {"with_sources": True}}}),
    ("GET", "/api/v1/metrics/weekly", {}),
    ("GET", "/api/v1/evaluations/00000000-0000-0000-0000-000000000000", {}),
    ("GET", "/api/v1/does-not-exist", {}),  # unknown routes under /api/v1 still need a session
]

COOKIE_CASES = {
    "no cookie": {},
    "forged session": {"__Host-session": "Zm9yZ2VkLXNlc3Npb24tdmFsdWUtMTIzNDU2Nzg5MA"},
    "garbage session": {"__Host-session": "%%%not-base64%%%"},
    "empty session": {"__Host-session": ""},
}


@pytest.mark.parametrize(("method", "path", "kw"), ROUTES)
@pytest.mark.parametrize("case", list(COOKIE_CASES))
async def test_requests_without_valid_session_are_rejected(method, path, kw, case):
    container, _ = make_container()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(container)),
        base_url="https://testserver",
        cookies=COOKIE_CASES[case],
    ) as c:
        r = await c.request(method, path, **kw)
    assert r.status_code == 401, (case, method, path, r.status_code)
    assert "items" not in r.text and "fileName" not in r.text  # nothing about documents leaks


@pytest.mark.parametrize(("method", "path", "kw"), [r for r in ROUTES if r[0] in ("POST", "DELETE")])
@pytest.mark.parametrize("token", [None, "", "wrong-token"])
async def test_unsafe_requests_need_csrf_token(client, method, path, kw, token):
    await login(client)
    headers = {} if token is None else {"X-CSRF-Token": token}
    r = await client.request(method, path, headers=headers, **kw)
    assert r.status_code == 403 and r.json()["code"] == "CSRF_INVALID"


async def test_csrf_token_of_another_session_is_rejected(stack):
    container, _ = stack
    app = create_app(container)
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="https://testserver") as a,
        httpx.AsyncClient(transport=transport, base_url="https://testserver") as b,
    ):
        await login(a, "member")
        await login(b, "member2")
        r = await a.post("/api/v1/documents", headers=csrf_headers(b), **UPLOAD)
        assert r.status_code == 403


async def test_expired_session_is_rejected_even_with_csrf(client, stack):
    _, f = stack
    await login(client)
    f.clock.advance(hours=9)
    r = await client.post("/api/v1/documents", headers=csrf_headers(client), **UPLOAD)
    assert r.status_code == 401


async def test_deactivated_user_is_rejected(client, stack):
    _, f = stack
    await login(client)
    u = next(iter(f.users.by_email.values()))
    f.users.by_email[u.email.lower()] = u.__class__(u.id, u.email, u.display_name, u.role, active=False)
    assert (await client.get("/api/v1/me")).status_code == 401
