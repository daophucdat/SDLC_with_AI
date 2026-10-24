from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from chatdocs.adapters.http.main import create_app
from tests.fakes import make_container


@pytest.fixture
def stack():
    """(container, fakes) wired with in-memory adapters."""
    return make_container()


@pytest.fixture
async def client(stack):
    container, _ = stack
    app = create_app(container)
    # https so the Secure / __Host- cookies are sent back, exactly as in production.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://testserver", follow_redirects=False
    ) as c:
        yield c


async def login(client: httpx.AsyncClient, who: str = "member", return_to: str = "/") -> httpx.Response:
    """Drive the real /auth/login → IdP → /auth/callback flow with the fake IdP."""
    r = await client.get("/auth/login", params={"returnTo": return_to})
    assert r.status_code == 302, r.text
    state = parse_qs(urlsplit(r.headers["location"]).query)["state"][0]
    return await client.get("/auth/callback", params={"code": who, "state": state})


def csrf_headers(client: httpx.AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("__Host-csrf") or ""}


def pdf_bytes(text: str = "Hop dong khach hang X. Thanh toan 30% khi ky.") -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


TRACE_RE = re.compile(r"^[0-9a-f]{32}$")
