import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.domain.enums import JobCategory, RemotePreference, WorkAuthorization


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthConfigResponse(BaseModel):
    skip_auth: bool
    default_email: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    legal_name: str
    location_city: str
    location_province: str
    work_authorization: str
    immigration_goals: dict[str, Any] = Field(
        description="e.g. express_entry, target_noc_codes, pei_pnp, preferred_pnp_provinces"
    )
    preferred_provinces: list[str] = Field(
        description="Canadian province codes for job search, e.g. PE, ON, BC"
    )
    preferred_job_categories: list[str] = Field(
        description="Role families: production, construction, it, ai, general"
    )
    skills: list[str]
    salary_min_cad: int | None = Field(description="Minimum acceptable salary in CAD")
    salary_max_cad: int | None = Field(description="Maximum target salary in CAD")
    remote_preference: str
    languages: dict[str, Any] = Field(
        description="e.g. english: fluent, french: intermediate"
    )
    phone: str
    linkedin_url: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    legal_name: str | None = None
    location_city: str | None = None
    location_province: str | None = None
    work_authorization: WorkAuthorization | None = None
    immigration_goals: dict[str, Any] | None = Field(
        default=None,
        description="Immigration pathway goals: express_entry, target_noc_codes, pei_pnp, etc.",
    )
    preferred_provinces: list[str] | None = Field(
        default=None,
        description="Province codes where the user wants to work, e.g. ['PE', 'ON']",
    )
    preferred_job_categories: list[JobCategory] | None = Field(
        default=None,
        description="Preferred role families for job matching",
    )
    skills: list[str] | None = None
    salary_min_cad: int | None = Field(default=None, ge=0)
    salary_max_cad: int | None = Field(default=None, ge=0)
    remote_preference: RemotePreference | None = None
    languages: dict[str, Any] | None = None
    phone: str | None = None
    linkedin_url: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
