"""US-101, US-102, US-103 through the HTTP API."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from tests.conftest import TRACE_RE, csrf_headers, login


async def test_login_flow_sets_session_and_me_works(client, stack):
    _, f = stack
    r = await client.get("/auth/login", params={"returnTo": "/metrics?weeks=4"})
    assert r.status_code == 302
    q = parse_qs(urlsplit(r.headers["location"]).query)
    assert q["code_challenge"][0] and q["state"][0]
    assert "__Host-oidc" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]

    r = await client.get("/auth/callback", params={"code": "member", "state": q["state"][0]})
    assert r.status_code == 302 and r.headers["location"] == "/metrics?weeks=4"  # AC-101.1 returns to the page
    cookies = r.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("__Host-session="))
    assert "HttpOnly" in session and "Secure" in session and "SameSite=lax" in session
    csrf = next(c for c in cookies if c.startswith("__Host-csrf="))
    assert "HttpOnly" not in csrf  # the SPA must read it

    me = await client.get("/api/v1/me")
    assert me.status_code == 200
    body = me.json()
    assert body["displayName"] == "Trần Thu Hà" and body["role"] == "BD_MEMBER" and body["permissions"] == []
    assert f.audit.actions() == ["login"]


async def test_session_survives_new_requests(client):
    await login(client)
    for _ in range(3):  # AC-101.2: reopening the tab within the session needs no new login
        assert (await client.get("/api/v1/me")).status_code == 200


async def test_lead_gets_advertised_permissions(client):
    await login(client, "lead")
    body = (await client.get("/api/v1/me")).json()
    assert body["role"] == "BD_LEAD"
    assert set(body["permissions"]) == {"documents:remove_any", "metrics:view", "evaluation:run"}


async def test_outsider_is_denied_without_session(client, stack):
    _, f = stack
    r = await login(client, "outsider")
    assert r.status_code == 302 and r.headers["location"] == "/denied"  # US-102 / EC-18
    assert not any(c.startswith("__Host-session=") for c in r.headers.get_list("set-cookie"))
    assert (await client.get("/api/v1/me")).status_code == 401
    assert f.audit.actions() == ["access_denied"]
    assert f.users.by_email == {}  # no account is created for denied users


async def test_idp_errors_and_state_mismatch_go_to_login_page(client, stack):
    _, f = stack
    r = await client.get("/auth/login")
    state = parse_qs(urlsplit(r.headers["location"]).query)["state"][0]
    r = await client.get("/auth/callback", params={"code": "broken", "state": state})
    assert r.headers["location"] == "/login?error=idp"  # AC-101.3
    r = await client.get("/auth/callback", params={"code": "member", "state": "forged"})
    assert r.headers["location"] == "/login?error=state"
    r = await client.get("/auth/callback", params={"error": "access_denied"})
    assert r.headers["location"] == "/login?error=idp"
    f.idp.down = True
    r = await client.get("/auth/login")
    assert r.headers["location"] == "/login?error=idp"


async def test_open_redirect_is_blocked(client):
    r = await login(client, return_to="https://evil.example/phish")
    assert r.headers["location"] == "/"


async def test_idle_session_expires_after_8_hours(client, stack):
    _, f = stack
    await login(client)
    f.clock.advance(hours=7, minutes=59)
    assert (await client.get("/api/v1/me")).status_code == 200  # activity resets the idle timer
    f.clock.advance(hours=8, minutes=1)
    r = await client.get("/api/v1/me")
    assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED"  # US-103
    assert f.sessions.rows == {}


async def test_activity_touch_is_throttled(client, stack):
    _, f = stack
    await login(client)
    for _ in range(5):
        await client.get("/api/v1/me")
    assert f.sessions.touches == 0
    f.clock.advance(minutes=2)
    await client.get("/api/v1/me")
    assert f.sessions.touches == 1


async def test_logout_requires_csrf_and_deletes_session(client, stack):
    _, f = stack
    await login(client)
    assert (await client.post("/auth/logout")).status_code == 403
    r = await client.post("/auth/logout", headers=csrf_headers(client))
    assert r.status_code == 204
    assert f.sessions.rows == {}
    assert "logout" in f.audit.actions()
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_problem_json_shape(client):
    r = await client.get("/api/v1/me")
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["status"] == 401 and body["code"] == "AUTH_REQUIRED" and TRACE_RE.match(body["traceId"])


async def test_health_endpoints(client, stack):
    _, f = stack
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    assert (await client.get("/readyz")).status_code == 200
    f.storage.healthy = False
    r = await client.get("/readyz")
    assert r.status_code == 503 and r.json()["checks"]["storage"] is False


async def test_unknown_api_route_is_404_only_after_login(client):
    assert (await client.get("/api/v1/nope")).status_code == 401
    await login(client)
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"
