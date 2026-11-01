from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AgentMessageRequest(BaseModel):
    org_id: UUID
    employee_id: UUID
    message: str = Field(min_length=1, max_length=16000)
    thread_key: str | None = Field(None, max_length=200)
    request_key: UUID | None = None
    use_meko: bool = True
    allow_tools: bool = False


class AgentMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    org_id: UUID
    employee_id: UUID
    platform: str
    thread_key: str
    input: str
    output: str | None
    recalled: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    delivery_status: str
    status: str
    capture_status: str
    error: str | None
    meko_conversation_id: str | None
    created_at: datetime
