"""Generic OIDC adapter (IF-01): discovery, Authorization Code + PKCE, ID-token validation with a cached JWKS.
Works with Keycloak (dev), Entra ID or Google Workspace (DEP-002) — only configuration differs."""

from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx
from authlib.jose import JsonWebKey, jwt
from authlib.jose.errors import JoseError

from chatdocs.domain.errors import IdentityProviderError
from chatdocs.ports.identity import IdTokenClaims

JWKS_TTL_SECONDS = 3600


def _origin(url: str) -> str:
    scheme, _, rest = url.partition("://")
    return f"{scheme}://{rest.split('/', 1)[0]}"


class OidcProvider:
    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        client_secret: str | None,
        groups_claim: str,
        http: httpx.AsyncClient | None = None,
        internal_base_url: str | None = None,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        # Containers often cannot reach the IdP by its public name (dev: "localhost:8080" is the API container
        # itself). Server-to-server calls then go to `internal_base_url`; the browser URL and `iss` stay public.
        self._public_base = _origin(self._issuer)
        self._internal_base = internal_base_url.rstrip("/") if internal_base_url else None
        self._client_id, self._client_secret, self._groups_claim = client_id, client_secret, groups_claim
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0))
        self._discovery: dict | None = None
        self._jwks: tuple[float, object] | None = None

    def _backchannel(self, url: str) -> str:
        if self._internal_base and url.startswith(self._public_base):
            return self._internal_base + url[len(self._public_base) :]
        return url

    async def _config(self) -> dict:
        if self._discovery is None:
            try:
                r = await self._http.get(self._backchannel(f"{self._issuer}/.well-known/openid-configuration"))
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise IdentityProviderError("discovery failed") from e
            self._discovery = r.json()
        return self._discovery

    async def _keys(self, force: bool = False):
        if self._jwks and not force and time.monotonic() - self._jwks[0] < JWKS_TTL_SECONDS:
            return self._jwks[1]
        cfg = await self._config()
        try:
            r = await self._http.get(self._backchannel(cfg["jwks_uri"]))
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise IdentityProviderError("jwks fetch failed") from e
        keys = JsonWebKey.import_key_set(r.json())
        self._jwks = (time.monotonic(), keys)
        return keys

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        cfg = await self._config()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{cfg['authorization_endpoint']}?{query}"

    async def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str, nonce: str) -> IdTokenClaims:
        cfg = await self._config()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "client_id": self._client_id,
        }
        auth = (self._client_id, self._client_secret) if self._client_secret else None
        try:
            r = await self._http.post(self._backchannel(cfg["token_endpoint"]), data=data, auth=auth)
            r.raise_for_status()
            id_token = r.json()["id_token"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise IdentityProviderError("token exchange failed") from e
        claims = await self._validate(id_token, nonce)
        email = str(claims.get("email") or claims.get("preferred_username") or "")
        if not email:
            raise IdentityProviderError("id_token has no email")
        groups = claims.get(self._groups_claim) or []
        if isinstance(groups, str):
            groups = [groups]
        # Access/ID tokens are not kept after login (SAD §4.1).
        return IdTokenClaims(
            subject=str(claims["sub"]),
            email=email,
            name=str(claims.get("name") or email),
            groups=[str(g) for g in groups],
        )

    async def _validate(self, id_token: str, nonce: str) -> dict:
        options = {
            "iss": {"essential": True, "value": self._issuer},
            "aud": {"essential": True, "value": self._client_id},
            "exp": {"essential": True},
            "nonce": {"essential": True, "value": nonce},
        }
        for force in (False, True):  # retry once with fresh keys (key rotation)
            try:
                claims = jwt.decode(id_token, await self._keys(force=force), claims_options=options)
                claims.validate(leeway=60)
                return dict(claims)
            except JoseError as e:
                last = e
        raise IdentityProviderError("invalid id_token") from last
