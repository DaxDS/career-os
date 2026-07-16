import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicationScreenshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    file_path: str
    original_filename: str
    caption: str
    captured_at: datetime | None
    created_at: datetime


class ApplicationTrackingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    master_resume_id: uuid.UUID
    status: str
    version: int
    ats_fact_check_passed: bool | None
    approved_at: datetime | None
    submitted_at: datetime | None
    submission_url: str
    submission_method: str | None
    submission_notes: str
    review_notes: str
    reviewed_at: datetime | None
    generated_at: datetime
    screenshots: list[ApplicationScreenshotResponse] = Field(default_factory=list)


class TrackedApplicationSummary(BaseModel):
    application: ApplicationTrackingResponse
    job_title: str
    company: str
    location_province: str
    job_status: str


class ApproveApplicationRequest(BaseModel):
    approved: bool = True
    notes: str = ""


class RecordSubmissionRequest(BaseModel):
    submission_url: str = ""
    submission_method: str = "manual"
    notes: str = ""
    success: bool = True


class WithdrawApplicationRequest(BaseModel):
    notes: str = ""


class UploadScreenshotResponse(BaseModel):
    screenshot: ApplicationScreenshotResponse
