from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.channel_assignments.schemas import ChannelAssignmentResponse

_VALID_EMPLOYEE_TYPES_PATTERN = r"^(legal-compliance|support|hr|general|sales)$"


class CreateEmployeeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    employee_type: str = Field(
        ...,
        pattern=_VALID_EMPLOYEE_TYPES_PATTERN,
        description="One of: legal-compliance, support, hr, general, sales",
    )
    role: str | None = None
    personality: dict | None = None
    specialization: str | None = None
    duties: list[str] | None = None
    custom_instructions: str | None = Field(None, max_length=12000)
    auto_memory: bool = True
    memory_policy: dict | None = None
    escalation_policy: dict | None = None


class UpdateEmployeeRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    employee_type: str | None = Field(
        None,
        pattern=_VALID_EMPLOYEE_TYPES_PATTERN,
        description="One of: legal-compliance, support, hr, general, sales",
    )
    role: str | None = None
    personality: dict | None = None
    specialization: str | None = None
    duties: list[str] | None = None
    custom_instructions: str | None = Field(None, max_length=12000)
    auto_memory: bool | None = None
    memory_policy: dict | None = None
    escalation_policy: dict | None = None
    status: str | None = None


class DiscordTokenRequest(BaseModel):
    token: str


class SlackTokenRequest(BaseModel):
    token: str


class StatusRequest(BaseModel):
    status: str  # "active" | "inactive"


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    org_id: UUID
    name: str
    employee_type: str | None = None
    role: str | None = None
    personality: dict | None = None
    specialization: str | None = None
    duties: list | None = None
    custom_instructions: str | None = None
    auto_memory: bool = True
    meko_datapack_id: str | None = None
    memory_setup_error: str | None = None
    memory_policy: dict | None = None
    escalation_policy: dict | None = None
    mcp_connections: list | None = None
    status: str
    has_discord_token: bool
    has_slack_token: bool

    slack_team_name: str | None = None
    slack_bot_user_id: str | None = None
    channel_assignments: list[ChannelAssignmentResponse] = []
    created_at: datetime
    updated_at: datetime | None = None


class EmployeeMemoryProfileResponse(BaseModel):
    static: list[str]
    dynamic: list[str]
    search_total: int | None = None
    search_timing_ms: int | None = None


class EmployeeMemoryHistoryEntryResponse(BaseModel):
    id: str
    memory: str
    version: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    parent_memory_id: str | None = None
    root_memory_id: str | None = None
    is_latest: bool
    is_forgotten: bool


class EmployeeMemoryEntryResponse(BaseModel):
    id: str
    memory: str
    version: int | None = None
    is_latest: bool
    is_forgotten: bool
    is_static: bool
    is_inference: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    space_id: str | None = None
    org_id: str | None = None
    source_count: int | None = None
    parent_memory_id: str | None = None
    root_memory_id: str | None = None
    forget_after: datetime | None = None
    forget_reason: str | None = None
    metadata: dict | None = None
    memory_relations: dict[str, str] | None = None
    temporal_context: dict | None = None
    history: list[EmployeeMemoryHistoryEntryResponse]
    document_ids: list[str]


class EmployeeMemoryExplorerResponse(BaseModel):
    memory_entries: list[EmployeeMemoryEntryResponse]
    current_page: int
    total_items: int
    total_pages: int
    limit: int | None = None
