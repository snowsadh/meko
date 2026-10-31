from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    employee_id: UUID | None = None
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    status: str
    error_message: str | None = None
    uploaded_at: datetime
    source_type: str
    source_url: str | None = None
