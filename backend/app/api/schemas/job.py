import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class JobSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    source_type: str = Field(..., description="manual, api, or scraper")
    config: dict[str, Any] = Field(default_factory=dict)


class JobSourceUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class JobSourceResponse(BaseModel):
    id: uuid.UUID
    preset_key: str | None
    name: str
    source_type: str
    config: dict[str, Any]
    is_builtin: bool
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobSourcePresetResponse(BaseModel):
    preset_key: str
    name: str
    source_type: str
    connector_key: str
    config: dict[str, Any]


class JobImportItem(BaseModel):
    external_id: str | None = None
    source_url: str = ""
    title: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    location_city: str = ""
    location_province: str = ""
    remote_type: str | None = None
    description: str = ""
    date_posted: datetime | None = None
    salary_min_cad: int | None = None
    salary_max_cad: int | None = None
    raw_payload: dict[str, Any] | None = None


class JobImportRequest(BaseModel):
    source_id: uuid.UUID | None = None
    source_preset_key: str | None = Field(
        None,
        description="Canonical preset key, e.g. job_bank_canada, manual_url_import",
    )
    jobs: list[JobImportItem] = Field(..., min_length=1)


class JobPostingResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID | None
    external_id: str | None
    source_url: str
    title: str
    company: str
    location_city: str
    location_province: str
    remote_type: str | None
    description_preview: str
    role_family: str | None
    classification: dict[str, Any]
    status: str
    date_found: datetime
    date_posted: datetime | None
    salary_min_cad: int | None
    salary_max_cad: int | None
    created_at: datetime
    updated_at: datetime
    # Optional intelligence scores, defaulted last to preserve field ordering
    overall_score: int | None = None
    immigration_score: int | None = None

    model_config = {"from_attributes": True}


class JobImportResultItem(BaseModel):
    import_status: Literal["created", "duplicate"]
    match_reason: str | None = None
    job: JobPostingResponse


class JobImportResponse(BaseModel):
    results: list[JobImportResultItem]
    created: int
    duplicates: int


class JobUpdateRequest(BaseModel):
    status: str | None = None
    role_family: str | None = None
