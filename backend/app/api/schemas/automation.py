import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BrowserSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connector_key: str
    profile_path: str
    status: str
    browser_name: str
    last_used_at: datetime | None
    created_at: datetime


class AutomationActionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    details: dict[str, Any]
    created_at: datetime


class AutomationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    application_id: uuid.UUID
    browser_session_id: uuid.UUID | None
    connector_key: str
    status: str
    browser_name: str
    stop_before_submit: bool
    submitted: bool
    failure_reason: str | None
    result_metadata: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    submission_recorded_at: datetime | None
    created_at: datetime


class StartAutomationRequest(BaseModel):
    stop_before_submit: bool | None = None


class StartAutomationResponse(BaseModel):
    run_id: uuid.UUID
    session_id: uuid.UUID | None = None
    status: str
    submitted: bool = False
    connector_key: str = ""
    browser: str = ""
    paused_for_captcha: bool = False
    failure_reason: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
