import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MasterResumeResponse(BaseModel):
    id: uuid.UUID
    label: str
    category: str
    original_filename: str
    is_active: bool
    version: int
    role_families: list[str]
    classification: dict[str, Any]
    content_hash: str
    uploaded_at: datetime
    parsed_preview: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ResumeVersionResponse(BaseModel):
    id: uuid.UUID
    master_resume_id: uuid.UUID
    version_number: int
    original_filename: str
    content_hash: str
    classification: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeLabelsResponse(BaseModel):
    labels: list[str]
