from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class MemorySourceCreate(BaseModel):
    org_id: UUID
    employee_id: UUID | None = None
    source_type: str = Field(..., pattern=r"^(text|url)$")
    scope: str = Field(..., pattern=r"^(org|employee)$")
    title: str | None = Field(None, max_length=500)
    content_text: str | None = None
    source_url: str | None = Field(None, max_length=2048)
    created_by_user_id: UUID | None = None

    @model_validator(mode="after")
    def validate_content(self) -> "MemorySourceCreate":
        if self.source_type == "text" and not self.content_text:
            raise ValueError("content_text is required when source_type is 'text'")
        if self.source_type == "url" and not self.source_url:
            raise ValueError("source_url is required when source_type is 'url'")
        if self.source_type == "text" and self.source_url:
            raise ValueError("source_url must be empty when source_type is 'text'")
        if self.source_type == "url" and self.content_text:
            raise ValueError("content_text must be empty when source_type is 'url'")
        if self.scope == "employee" and not self.employee_id:
            raise ValueError("employee_id is required when scope is 'employee'")
        if self.scope == "org" and self.employee_id:
            raise ValueError("employee_id must be empty when scope is 'org'")
        return self


class MemorySourceUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    employee_id: UUID | None = None


class CreateTextMemorySourceRequest(BaseModel):
    scope: str = Field(..., pattern=r"^(org|employee)$")
    employee_id: UUID | None = None
    title: str | None = Field(None, max_length=500)
    content_text: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_scope(self) -> "CreateTextMemorySourceRequest":
        if self.scope == "employee" and not self.employee_id:
            raise ValueError("employee_id is required when scope is 'employee'")
        if self.scope == "org" and self.employee_id:
            raise ValueError("employee_id must be empty when scope is 'org'")
        return self


class CreateUrlMemorySourceRequest(BaseModel):
    scope: str = Field(..., pattern=r"^(org|employee)$")
    employee_id: UUID | None = None
    title: str | None = Field(None, max_length=500)
    source_url: str = Field(..., min_length=1, max_length=2048)

    @model_validator(mode="after")
    def validate_scope(self) -> "CreateUrlMemorySourceRequest":
        if self.scope == "employee" and not self.employee_id:
            raise ValueError("employee_id is required when scope is 'employee'")
        if self.scope == "org" and self.employee_id:
            raise ValueError("employee_id must be empty when scope is 'org'")
        return self


class MemorySourceResponse(BaseModel):
    id: UUID
    org_id: UUID
    employee_id: UUID | None = None
    source_type: str
    scope: str
    title: str | None = None
    content_text: str | None = None
    source_url: str | None = None
    provider_memory_id: str | None = None
    meko_document_id: str | None = None
    origin_memory_id: str | None = None
    origin_employee_id: UUID | None = None
    size_bytes: int | None = None
    status: str
    error_message: str | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
