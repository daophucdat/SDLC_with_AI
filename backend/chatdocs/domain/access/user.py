from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Role(str, Enum):
    BD_MEMBER = "BD_MEMBER"
    BD_LEAD = "BD_LEAD"
    MANAGER = "MANAGER"


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    display_name: str
    role: Role
    active: bool = True
