"""Map IdP groups to an application role (US-101, US-102). Highest role wins: LEAD > MANAGER > MEMBER."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from chatdocs.domain.access.user import Role


@dataclass(frozen=True)
class RoleGroups:
    member: str
    lead: str
    manager: str


def _normalise(group: str) -> str:
    # Keycloak sends group paths ("/grp-bd-lead"); Entra / Google send plain names. Compare case-insensitively.
    return group.strip().lstrip("/").rsplit("/", 1)[-1].lower()


def role_from_groups(groups: Iterable[str], mapping: RoleGroups) -> Role | None:
    names = {_normalise(g) for g in groups if g}
    if _normalise(mapping.lead) in names:
        return Role.BD_LEAD
    if _normalise(mapping.manager) in names:
        return Role.MANAGER
    if _normalise(mapping.member) in names:
        return Role.BD_MEMBER
    return None
