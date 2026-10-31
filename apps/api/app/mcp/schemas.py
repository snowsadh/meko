from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class McpConnectionCreate(BaseModel):
    credential: str = Field(min_length=1)
    auth_type: str = "api_key_header"
    server_url: str | None = None
    scopes: list[str] | None = None
    org_wide: bool = False


class McpConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    connector_slug: str
    auth_type: str
    scopes: list | None = None
    status: str
    created_at: datetime


class McpConnectionList(BaseModel):
    connections: list[McpConnectionRead]


class McpConnectorRead(BaseModel):
    slug: str
    name: str
    description: str
    auth_type: str
    auth_types: list[str]
    requires_custom_server_url: bool = False
    is_connected: bool = False
