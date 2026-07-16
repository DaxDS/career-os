import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineStepLogEntry(BaseModel):
    step: str
    status: str | None = None
    model_config = {"extra": "allow"}


class PipelineRunResponse(BaseModel):
    id: uuid.UUID
    trigger_type: str
    scope: str
    scope_filter: dict[str, Any]
    status: str
    step_log: list[dict[str, Any]]
    summary: dict[str, Any]
    notification_sent: bool
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineNotificationResponse(BaseModel):
    id: uuid.UUID
    pipeline_run_id: uuid.UUID
    message: str
    details: dict[str, Any]
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SchedulerStatusResponse(BaseModel):
    enabled: bool
    running: bool
    schedule_hour: int | None = None
    schedule_minute: int | None = None
    timezone: str | None = None
    next_run_at: str | None = None


class CompanyPipelineRequest(BaseModel):
    company: str = Field(..., min_length=1)
    source_id: uuid.UUID | None = None
