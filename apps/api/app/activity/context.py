"""Request context used by agent and gateway activity recording."""

from __future__ import annotations

import contextvars

activity_org_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("activity_org_id", default=None)
activity_employee_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("activity_employee_id", default=None)
activity_employee_name: contextvars.ContextVar[str | None] = contextvars.ContextVar("activity_employee_name", default=None)
activity_platform: contextvars.ContextVar[str] = contextvars.ContextVar("activity_platform", default="api")
activity_channel_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("activity_channel_id", default=None)
