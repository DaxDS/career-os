import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobScoreResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    ats_score: int | None
    match_score: int | None
    immigration_score: int | None
    pr_score: int | None
    overall_score: int | None
    selected_master_resume_id: uuid.UUID | None
    resume_selection_confidence: float | None
    immigration_details: dict[str, Any]
    ats_details: dict[str, Any]
    match_details: dict[str, Any]
    selection_details: dict[str, Any]
    scoring_method: str
    scored_at: datetime

    model_config = {"from_attributes": True}


class RankedJobResponse(BaseModel):
    job_id: uuid.UUID
    title: str
    company: str
    location_province: str
    role_family: str | None
    overall_score: int | None
    selected_master_resume_id: uuid.UUID | None
    scored_at: datetime


class BatchAnalyzeResponse(BaseModel):
    analyzed: int
    job_score_ids: list[uuid.UUID]


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    agent_name: str
    capability: str
    status: str
    output: dict[str, Any]
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PipelineRunRequest(BaseModel):
    limit: int = Field(20, ge=1, le=100)
