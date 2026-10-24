from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class IdTokenClaims:
    subject: str
    email: str
    name: str
    groups: list[str] = field(default_factory=list)


class IdentityProvider(Protocol):
    """IF-01. Raises chatdocs.domain.errors.IdentityProviderError on any IdP / token problem."""

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str: ...

    async def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str, nonce: str) -> IdTokenClaims: ...
