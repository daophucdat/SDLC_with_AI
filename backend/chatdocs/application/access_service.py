"""AccessService — US-101 (login), US-102 (deny non-BD users), US-103 (idle expiry, logout)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from chatdocs.domain.access.role_mapping import RoleGroups, role_from_groups
from chatdocs.domain.access.user import User
from chatdocs.domain.errors import AuthRequired, ForbiddenRole
from chatdocs.platform.security import b64url_decode, csrf_token_for, new_token, pkce_pair, safe_return_to, sha256
from chatdocs.ports.clock import Clock
from chatdocs.ports.identity import IdentityProvider
from chatdocs.ports.qa import AnalyticsSink
from chatdocs.ports.repositories import AuditLog, SessionRepository, UserRepository

TOUCH_EVERY = timedelta(minutes=1)  # write last_activity_at at most once a minute (SAD §3.2.1 step 3)


@dataclass(frozen=True)
class LoginStart:
    authorization_url: str
    state: str
    nonce: str
    code_verifier: str
    return_to: str


@dataclass(frozen=True)
class LoginResult:
    session_token: str
    csrf_token: str
    user: User
    first_session: bool


@dataclass(frozen=True)
class AuthContext:
    user: User
    session_id_hash: bytes
    csrf_secret: bytes


class AccessService:
    def __init__(
        self,
        *,
        idp: IdentityProvider,
        users: UserRepository,
        sessions: SessionRepository,
        audit: AuditLog,
        role_groups: RoleGroups,
        idle_hours: int,
        redirect_uri: str,
        clock: Clock,
        analytics: AnalyticsSink | None = None,
    ) -> None:
        self._idp, self._users, self._sessions, self._audit = idp, users, sessions, audit
        self._role_groups, self._idle = role_groups, timedelta(hours=idle_hours)
        self._redirect_uri, self._clock = redirect_uri, clock
        self._analytics = analytics

    async def begin_login(self, return_to: str | None) -> LoginStart:
        state, nonce = new_token(24), new_token(24)
        verifier, challenge = pkce_pair()
        url = await self._idp.authorization_url(
            state=state, nonce=nonce, code_challenge=challenge, redirect_uri=self._redirect_uri
        )
        return LoginStart(url, state, nonce, verifier, safe_return_to(return_to))

    async def complete_login(self, *, code: str, code_verifier: str, nonce: str, ip: str | None) -> LoginResult:
        claims = await self._idp.exchange_code(
            code=code, code_verifier=code_verifier, redirect_uri=self._redirect_uri, nonce=nonce
        )
        role = role_from_groups(claims.groups, self._role_groups)
        if role is None:
            await self._audit.record(
                action="access_denied", actor_id=None, target_type="email", target_id=claims.email.lower(), ip=ip
            )
            if self._analytics:
                self._analytics.emit("access_denied", {"reason": "no_group"}, user_id=None, session_id=None)
            raise ForbiddenRole()

        now = self._clock.now()
        user, created = await self._users.upsert_login(
            email=claims.email, display_name=claims.name or claims.email, role=role, now=now
        )
        token = new_token(32)
        csrf_secret = secrets.token_bytes(32)
        await self._sessions.create(id_hash=sha256(token), user_id=user.id, csrf_secret=csrf_secret, now=now)
        await self._audit.record(action="login", actor_id=user.id, ip=ip)
        if self._analytics:
            self._analytics.emit(
                "session_started", {"is_first_session": created}, user_id=user.id, session_id=sha256(token).hex()[:16]
            )
        return LoginResult(token, csrf_token_for(csrf_secret), user, first_session=created)

    async def authenticate(self, session_token: str | None) -> AuthContext:
        if not session_token:
            raise AuthRequired()
        try:
            b64url_decode(session_token)
        except ValueError:
            raise AuthRequired() from None
        id_hash = sha256(session_token)
        record = await self._sessions.get(id_hash)
        if record is None or not record.user.active:
            raise AuthRequired()
        now = self._clock.now()
        if now - record.last_activity_at > self._idle:  # US-103: 8 h without activity
            await self._sessions.delete(id_hash)
            raise AuthRequired("session expired")
        if now - record.last_activity_at >= TOUCH_EVERY:
            await self._sessions.touch(id_hash, now)
        return AuthContext(record.user, id_hash, record.csrf_secret)

    async def csrf_secret_of(self, session_token: str | None) -> bytes | None:
        """CSRF secret of an existing session (even an idle one), so logout can be CSRF-checked."""
        if not session_token:
            return None
        record = await self._sessions.get(sha256(session_token))
        return record.csrf_secret if record else None

    async def sweep_idle(self) -> int:
        """Job sweep_sessions every 15 min (US-103 T103.1); conversations are deleted with their session (PD-04)."""
        return await self._sessions.delete_idle(self._clock.now() - self._idle)

    async def logout(self, session_token: str | None, ip: str | None) -> None:
        if not session_token:
            return
        id_hash = sha256(session_token)
        record = await self._sessions.get(id_hash)
        await self._sessions.delete(id_hash)  # conversations cascade with the session (PD-04)
        if record:
            await self._audit.record(action="logout", actor_id=record.user.id, ip=ip)
