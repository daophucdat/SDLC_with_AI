"""PermissionPolicy (PRD §6.3, PD-02). Every application service calls `can()`; routers are not the only gate."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from chatdocs.domain.access.user import Role, User


class Action(str, Enum):
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPLOAD = "documents:upload"
    DOCUMENTS_REMOVE = "documents:remove"  # needs the resource owner
    DOCUMENTS_REMOVE_ANY = "documents:remove_any"
    QA_ASK = "qa:ask"
    METRICS_VIEW = "metrics:view"
    EVALUATION_RUN = "evaluation:run"


_ALL_ROLES = {Role.BD_MEMBER, Role.BD_LEAD, Role.MANAGER}
_GRANTS: dict[Action, set[Role]] = {
    Action.DOCUMENTS_READ: _ALL_ROLES,
    Action.DOCUMENTS_UPLOAD: _ALL_ROLES,
    Action.QA_ASK: _ALL_ROLES,
    Action.DOCUMENTS_REMOVE_ANY: {Role.BD_LEAD},
    Action.METRICS_VIEW: {Role.BD_LEAD, Role.MANAGER},
    Action.EVALUATION_RUN: {Role.BD_LEAD},
}

# Shown to the frontend (/api/v1/me) so it can hide controls; the server still checks every call.
_ADVERTISED = (Action.DOCUMENTS_REMOVE_ANY, Action.METRICS_VIEW, Action.EVALUATION_RUN)


def can(user: User, action: Action, owner_id: UUID | None = None) -> bool:
    if not user.active:
        return False
    if action is Action.DOCUMENTS_REMOVE:
        return user.role in _GRANTS[Action.DOCUMENTS_REMOVE_ANY] or (owner_id is not None and owner_id == user.id)
    return user.role in _GRANTS.get(action, set())


def advertised_permissions(user: User) -> list[str]:
    return [a.value for a in _ADVERTISED if can(user, a)]
