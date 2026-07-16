import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReviewQueueItemResponse(BaseModel):
    application_id: uuid.UUID
    job_id: uuid.UUID
    title: str
    company: str
    location_province: str
    overall_score: int | None
    ats_fact_check_passed: bool | None
    resume_summary_preview: str
    cover_letter_preview: str
    generated_at: datetime
    version: int
    match_score: int | None = None
    ats_score: int | None = None
    immigration_score: int | None = None


class ReviewStatsResponse(BaseModel):
    pending_review: int
    revision_requested: int
    rejected: int
    approved: int


class ReviewDetailResponse(BaseModel):
    application_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    version: int
    ats_fact_check_passed: bool | None
    review_notes: str
    generated_at: datetime
    title: str
    company: str
    location_province: str
    overall_score: int | None
    document_previews: dict[str, Any]
    match_score: int | None = None
    ats_score: int | None = None
    immigration_score: int | None = None


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="approve, reject, or request_revision")
    notes: str = ""


class ReviewDecisionResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    review_notes: str
    reviewed_at: datetime | None


class BatchReviewRequest(BaseModel):
    job_ids: list[uuid.UUID] = Field(..., min_length=1)
    decision: str
    notes: str = ""


class BatchReviewItemResponse(BaseModel):
    job_id: uuid.UUID
    success: bool
    status: str | None = None
    error: str | None = None


class BatchReviewResponse(BaseModel):
    results: list[BatchReviewItemResponse]
    succeeded: int
    failed: int
