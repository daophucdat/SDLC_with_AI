from __future__ import annotations

import json
import logging
import time

import pytest
import structlog

from chatdocs.platform import security
from chatdocs.platform.logging import REDACTED, configure_logging, redact_content


def test_pkce_challenge_is_s256_of_verifier():
    verifier, challenge = security.pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert challenge == security.b64url(security.sha256(verifier))


def test_sign_unsign_roundtrip_tamper_and_expiry(monkeypatch):
    token = security.sign({"s": "abc"}, "k" * 20, ttl_seconds=60)
    assert security.unsign(token, "k" * 20)["s"] == "abc"
    assert security.unsign(token, "other-secret-xxxxx") is None
    raw, mac = token.rsplit(".", 1)
    assert security.unsign(raw + "x." + mac, "k" * 20) is None
    assert security.unsign(None, "k" * 20) is None
    real = time.time
    monkeypatch.setattr(security.time, "time", lambda: real() + 120)
    assert security.unsign(token, "k" * 20) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/", "/"),
        ("/metrics?weeks=4", "/metrics?weeks=4"),
        (None, "/"),
        ("https://evil.com", "/"),
        ("//evil.com/x", "/"),
        ("/\\evil.com", "/"),
        ("javascript:alert(1)", "/"),
        ("metrics", "/"),
    ],
)
def test_safe_return_to(value, expected):
    assert security.safe_return_to(value) == expected


def test_csrf_double_submit_bound_to_session_secret():
    secret = b"s" * 32
    token = security.csrf_token_for(secret)
    assert security.csrf_valid(secret, token, token)
    assert not security.csrf_valid(secret, token, "other")
    assert not security.csrf_valid(secret, None, token)
    assert not security.csrf_valid(b"x" * 32, token, token)  # token from another session


def test_redaction_processor_removes_content_fields():
    event = redact_content(
        None,
        "info",
        {"event": "x", "question": "ZZZ-SECRET", "text": "t", "meta": {"excerpt": "e", "page": 4}, "count": 3},
    )
    assert event["question"] == REDACTED and event["text"] == REDACTED
    assert event["meta"] == {"excerpt": REDACTED, "page": 4}
    assert event["count"] == 3


def test_configured_logger_never_prints_content(capsys):
    configure_logging("INFO")
    structlog.get_logger("t").info("asked", question="ZZZ-SECRET hợp đồng", question_length=12)
    out = capsys.readouterr().out
    assert "ZZZ-SECRET" not in out
    line = json.loads(out.strip().splitlines()[-1])
    assert line["question_length"] == 12 and line["question"] == REDACTED
    logging.getLogger().handlers.clear()


async def test_oidc_backchannel_uses_internal_base_url():
    import httpx

    from chatdocs.adapters.oidc.generic import OidcProvider

    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "authorization_endpoint": "http://localhost:8080/realms/c/protocol/openid-connect/auth",
                "token_endpoint": "http://localhost:8080/realms/c/protocol/openid-connect/token",
                "jwks_uri": "http://localhost:8080/realms/c/protocol/openid-connect/certs",
            },
        )

    idp = OidcProvider(
        issuer="http://localhost:8080/realms/c",
        client_id="x",
        client_secret=None,
        groups_claim="groups",
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        internal_base_url="http://keycloak:8080",
    )
    url = await idp.authorization_url(state="s", nonce="n", code_challenge="c", redirect_uri="http://localhost/cb")
    assert seen == ["http://keycloak:8080/realms/c/.well-known/openid-configuration"]
    assert url.startswith(
        "http://localhost:8080/realms/c/protocol/openid-connect/auth?"
    )  # the browser URL stays public
    assert idp._backchannel("http://localhost:8080/realms/c/protocol/openid-connect/token").startswith(
        "http://keycloak:8080/"
    )
