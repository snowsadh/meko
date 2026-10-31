from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    employee_id: UUID | None = None
    limit: int = Field(10, ge=1, le=50)
    threshold: float | None = Field(None, ge=0, le=1)
    chunk_threshold: float | None = Field(None, ge=0, le=1)
    only_matching_chunks: bool | None = None


class MemorySearchResultResponse(BaseModel):
    provider_result_id: str
    document_id: str | None = None
    container_tag: str
    score: float | None = None
    content: str | None = None
    chunks: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None
    version: int | None = None


class MemorySearchResponse(BaseModel):
    query: str
    tags: list[str]
    results: list[MemorySearchResultResponse]
    total: int


class CreateMemoryTextRequest(BaseModel):
    scope: str = Field(..., pattern=r"^(org|employee)$")
    employee_id: UUID | None = None
    title: str | None = Field(None, max_length=500)
    content_text: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_scope(self) -> "CreateMemoryTextRequest":
        if self.scope == "employee" and self.employee_id is None:
            raise ValueError("employee_id is required when scope is 'employee'")
        if self.scope == "org" and self.employee_id is not None:
            raise ValueError("employee_id must be empty when scope is 'org'")
        return self


class CreateMemoryUrlRequest(BaseModel):
    scope: str = Field(..., pattern=r"^(org|employee)$")
    employee_id: UUID | None = None
    title: str | None = Field(None, max_length=500)
    source_url: str = Field(..., min_length=1, max_length=2048)

    @model_validator(mode="after")
    def validate_scope(self) -> "CreateMemoryUrlRequest":
        if self.scope == "employee" and self.employee_id is None:
            raise ValueError("employee_id is required when scope is 'employee'")
        if self.scope == "org" and self.employee_id is not None:
            raise ValueError("employee_id must be empty when scope is 'org'")
        return self
