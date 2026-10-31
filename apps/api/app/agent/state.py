from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class AgentContext(TypedDict, total=False):
    org_id: UUID
    employee_id: UUID
    user_id: UUID
    platform: str
    query: str
    response: str
