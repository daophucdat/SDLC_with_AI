"""Small, dependency-free security helpers (session tokens, PKCE, signed cookies, CSRF, safe redirects)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlsplit


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def new_token(n_bytes: int = 32) -> str:
    return b64url(secrets.token_bytes(n_bytes))


def sha256(data: bytes | str) -> bytes:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).digest()


def pkce_pair() -> tuple[str, str]:
    """(code_verifier, S256 code_challenge) — RFC 7636."""
    verifier = new_token(48)
    return verifier, b64url(sha256(verifier))


def csrf_token_for(csrf_secret: bytes) -> str:
    return b64url(hmac.new(csrf_secret, b"csrf-v1", hashlib.sha256).digest())


def csrf_valid(csrf_secret: bytes, header: str | None, cookie: str | None) -> bool:
    if not header or not cookie or not hmac.compare_digest(header, cookie):
        return False
    return hmac.compare_digest(header, csrf_token_for(csrf_secret))


def sign(payload: dict, secret: str, ttl_seconds: int) -> str:
    body = dict(payload, exp=int(time.time()) + ttl_seconds)
    raw = b64url(json.dumps(body, separators=(",", ":")).encode())
    mac = b64url(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest())
    return f"{raw}.{mac}"


def unsign(value: str | None, secret: str) -> dict | None:
    if not value or "." not in value:
        return None
    raw, mac = value.rsplit(".", 1)
    expected = b64url(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(mac, expected):
        return None
    try:
        body = json.loads(b64url_decode(raw))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(body, dict) or body.get("exp", 0) < time.time():
        return None
    return body


def safe_return_to(value: str | None) -> str:
    """Only same-site relative paths; anything else (absolute URL, //host, backslashes) becomes '/'."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return "/"
    return value
