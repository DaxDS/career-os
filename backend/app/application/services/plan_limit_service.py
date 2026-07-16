"""Plan limit enforcement — checked at API entry points before paid actions."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.plans import PLAN_FREE, PLANS, plan_or_free
from app.infrastructure.db.models import JobPosting, MasterResume, User
from app.infrastructure.db.scheduler_models import PipelineRun


class PlanLimitExceeded(Exception):
    """Raised when an action would exceed the user's plan limits (HTTP 402)."""


def month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class PlanLimitService:
    def __init__(self, db: Session):
        self._db = db

    def get_plan_key(self, user_id: uuid.UUID) -> str:
        tier = self._db.scalar(select(User.plan_tier).where(User.id == user_id))
        return plan_or_free(tier)

    def _limits(self, user_id: uuid.UUID) -> dict[str, int]:
        return PLANS[self.get_plan_key(user_id)]["limits"]

    def pipeline_runs_this_month(self, user_id: uuid.UUID) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(PipelineRun)
                .where(PipelineRun.user_id == user_id, PipelineRun.created_at >= month_start())
            )
            or 0
        )

    def jobs_this_month(self, user_id: uuid.UUID) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(JobPosting)
                .where(JobPosting.user_id == user_id, JobPosting.created_at >= month_start())
            )
            or 0
        )

    def active_resume_count(self, user_id: uuid.UUID) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(MasterResume)
                .where(MasterResume.user_id == user_id, MasterResume.is_active.is_(True))
            )
            or 0
        )

    def ensure_pro_feature(self, user_id: uuid.UUID, feature: str) -> None:
        if self.get_plan_key(user_id) == PLAN_FREE:
            raise PlanLimitExceeded(
                f"{feature} is a Pro feature. Upgrade your plan to unlock it."
            )

    def ensure_can_run_pipeline(self, user_id: uuid.UUID) -> None:
        limit = self._limits(user_id)["ai_pipeline_runs"]
        used = self.pipeline_runs_this_month(user_id)
        if used >= limit:
            raise PlanLimitExceeded(
                f"Plan limit reached: {used}/{limit} AI pipeline runs this month. "
                "Upgrade your plan to keep running the pipeline."
            )

    def ensure_can_import_jobs(self, user_id: uuid.UUID, new_jobs: int = 1) -> None:
        limit = self._limits(user_id)["jobs_per_month"]
        used = self.jobs_this_month(user_id)
        if used + new_jobs > limit:
            raise PlanLimitExceeded(
                f"Plan limit reached: {used}/{limit} job imports this month. "
                "Upgrade your plan to import more jobs."
            )

    def ensure_can_upload_resume(self, user_id: uuid.UUID, label: str) -> None:
        # Replacing an existing active label is a version bump, not a new slot.
        existing = self._db.scalar(
            select(func.count())
            .select_from(MasterResume)
            .where(
                MasterResume.user_id == user_id,
                MasterResume.is_active.is_(True),
                MasterResume.label == label,
            )
        )
        if existing:
            return
        limit = self._limits(user_id)["resume_slots"]
        used = self.active_resume_count(user_id)
        if used >= limit:
            raise PlanLimitExceeded(
                f"Plan limit reached: {used}/{limit} resume tracks in use. "
                "Upgrade your plan or deactivate a resume to add another."
            )
