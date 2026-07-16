import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApplicationDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: str
    file_path: str
    content: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


class JobApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    master_resume_id: uuid.UUID
    status: str
    version: int
    ats_fact_check_passed: bool | None
    generation_metadata: dict[str, Any]
    generated_at: datetime
    documents: list[ApplicationDocumentResponse] = Field(default_factory=list)


class GenerateDocumentsResponse(BaseModel):
    application: JobApplicationResponse
    regenerated: bool = False
