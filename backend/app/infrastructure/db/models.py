from datetime import datetime
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import JobStatus, RemotePreference, WorkAuthorization
from app.infrastructure.db.base import Base


class SystemMetadata(Base):
    """Layer 0 bootstrap table — tracks schema layer and app version."""

    __tablename__ = "system_metadata"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuditLog(Base):
    """Immutable append-only audit trail."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PromptVersion(Base):
    """Versioned prompt content — synced from external files under /prompts."""

    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_prompt_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    """Single-user account (multi-user schema-ready)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan_tier: Mapped[str] = mapped_column(
        String(20), default="free", server_default="free", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    master_resumes: Mapped[list["MasterResume"]] = relationship(back_populates="user")
    job_sources: Mapped[list["JobSource"]] = relationship(back_populates="user")
    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="user")


class UserProfile(Base):
    """Career and immigration preferences for the job seeker."""

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location_city: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    location_province: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    work_authorization: Mapped[str] = mapped_column(
        String(50), default=WorkAuthorization.WORK_PERMIT.value, nullable=False
    )
    immigration_goals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    preferred_provinces: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preferred_job_categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    salary_min_cad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max_cad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remote_preference: Mapped[str] = mapped_column(
        String(20), default=RemotePreference.ANY.value, nullable=False
    )
    languages: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    linkedin_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class MasterResume(Base):
    """Permanent master resume — one active record per label per user."""

    __tablename__ = "master_resumes"
    __table_args__ = (UniqueConstraint("user_id", "label", name="uq_master_resume_user_label"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    role_families: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    classification: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="master_resumes")
    versions: Mapped[list["ResumeVersion"]] = relationship(back_populates="master_resume")


class ResumeVersion(Base):
    """Immutable history of master resume file revisions."""

    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("master_resumes.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    master_resume: Mapped["MasterResume"] = relationship(back_populates="versions")


class JobSource(Base):
    """Configured job ingestion source for a user."""

    __tablename__ = "job_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_job_source_user_name"),
        UniqueConstraint("user_id", "preset_key", name="uq_job_source_user_preset_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    preset_key: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="job_sources")
    postings: Mapped[list["JobPosting"]] = relationship(back_populates="source")


class JobPosting(Base):
    """Imported job posting with deduplication metadata."""

    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint("user_id", "source_id", "external_id", name="uq_job_user_source_external"),
        UniqueConstraint("user_id", "dedup_key", name="uq_job_user_dedup_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_sources.id"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2000), default="", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location_city: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    location_province: Mapped[str] = mapped_column(String(10), default="", nullable=False)
    remote_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role_family: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classification: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=JobStatus.NEW.value, nullable=False)
    is_duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_postings.id"), nullable=True
    )
    date_found: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_posted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    salary_min_cad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max_cad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="job_postings")
    source: Mapped["JobSource | None"] = relationship(back_populates="postings")
    score: Mapped["JobScore | None"] = relationship(back_populates="job", uselist=False)
    application: Mapped["JobApplication | None"] = relationship(
        back_populates="job", uselist=False
    )


class JobScore(Base):
    """Persisted intelligence scores and resume selection for a job posting."""

    __tablename__ = "job_scores"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_score_user_job"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    ats_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    immigration_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    selected_master_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("master_resumes.id"), nullable=True
    )
    resume_selection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    immigration_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ats_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    match_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    selection_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    scoring_method: Mapped[str] = mapped_column(String(50), default="llm", nullable=False)
    agent_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job: Mapped["JobPosting"] = relationship(back_populates="score")


class JobApplication(Base):
    """Generated application package for a job — resume, cover letter, email."""

    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    master_resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("master_resumes.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="generated", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ats_fact_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    generation_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_url: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    submission_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    submission_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job: Mapped["JobPosting"] = relationship(back_populates="application")
    documents: Mapped[list["ApplicationDocument"]] = relationship(back_populates="application")
    screenshots: Mapped[list["ApplicationScreenshot"]] = relationship(back_populates="application")


class ApplicationDocument(Base):
    """A single generated artifact within a job application package."""

    __tablename__ = "application_documents"
    __table_args__ = (
        UniqueConstraint("application_id", "document_type", name="uq_application_doc_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_applications.id"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    application: Mapped["JobApplication"] = relationship(back_populates="documents")


class ApplicationScreenshot(Base):
    """Confirmation screenshot captured after manual submission."""

    __tablename__ = "application_screenshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_applications.id"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["JobApplication"] = relationship(back_populates="screenshots")


class AgentRun(Base):
    """Record of a single agent invocation for debugging and audit."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    capability: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
