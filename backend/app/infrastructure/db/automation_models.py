from datetime import datetime
import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class BrowserSession(Base):
    """Persistent Playwright browser profile per user and job-source connector."""

    __tablename__ = "browser_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    profile_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_state_path: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="idle", nullable=False)
    browser_name: Mapped[str] = mapped_column(String(50), default="chromium", nullable=False)
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    runs: Mapped[list["AutomationRun"]] = relationship(back_populates="browser_session")


class AutomationRun(Base):
    """Playwright automation attempt for an approved job application."""

    __tablename__ = "automation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_applications.id"), nullable=False
    )
    browser_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("browser_sessions.id"), nullable=True
    )
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    browser_name: Mapped[str] = mapped_column(String(50), default="chromium", nullable=False)
    stop_before_submit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    browser_session: Mapped["BrowserSession | None"] = relationship(back_populates="runs")
    action_logs: Mapped[list["AutomationActionLog"]] = relationship(back_populates="run")


class AutomationActionLog(Base):
    """Immutable log entry for every browser automation action."""

    __tablename__ = "automation_action_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("automation_runs.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped["AutomationRun"] = relationship(back_populates="action_logs")
