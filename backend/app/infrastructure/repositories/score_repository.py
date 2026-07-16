import uuid
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.application.ports.score_repository import AgentRunRepositoryPort, ScoreRepositoryPort
from app.domain.enums import JobStatus
from app.infrastructure.db.models import AgentRun, JobPosting, JobScore


class SQLAlchemyScoreRepository(ScoreRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_by_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobScore | None:
        return (
            self._db.query(JobScore)
            .filter(JobScore.user_id == user_id, JobScore.job_id == job_id)
            .first()
        )

    def list_for_jobs(self, user_id: uuid.UUID, job_ids: list[uuid.UUID]) -> list[JobScore]:
        if not job_ids:
            return []
        return (
            self._db.query(JobScore)
            .filter(JobScore.user_id == user_id, JobScore.job_id.in_(job_ids))
            .all()
        )

    def upsert(self, score: JobScore) -> JobScore:
        existing = self.get_by_job(score.user_id, score.job_id)
        if existing:
            for field in (
                "ats_score",
                "match_score",
                "immigration_score",
                "pr_score",
                "overall_score",
                "selected_master_resume_id",
                "resume_selection_confidence",
                "immigration_details",
                "ats_details",
                "match_details",
                "selection_details",
                "scoring_method",
                "agent_metadata",
                "scored_at",
            ):
                setattr(existing, field, getattr(score, field))
            self._db.commit()
            self._db.refresh(existing)
            return existing
        self._db.add(score)
        self._db.commit()
        self._db.refresh(score)
        return score

    def list_ranked(
        self,
        user_id: uuid.UUID,
        *,
        min_overall_score: int | None = None,
        province: str | None = None,
        role_family: str | None = None,
        limit: int = 50,
    ) -> list[tuple[JobScore, JobPosting]]:
        q = (
            self._db.query(JobScore, JobPosting)
            .join(JobPosting, JobScore.job_id == JobPosting.id)
            .filter(JobScore.user_id == user_id, JobPosting.user_id == user_id)
            .filter(JobPosting.status != JobStatus.ARCHIVED.value)
        )
        if min_overall_score is not None:
            q = q.filter(JobScore.overall_score >= min_overall_score)
        if province:
            q = q.filter(JobPosting.location_province == province.upper())
        if role_family:
            q = q.filter(JobPosting.role_family == role_family)
        q = q.order_by(desc(JobScore.overall_score), desc(JobScore.scored_at))
        return q.limit(limit).all()

    def list_unscored_job_ids(self, user_id: uuid.UUID, limit: int = 20) -> list[uuid.UUID]:
        scored_ids = [
            row[0]
            for row in self._db.query(JobScore.job_id).filter(JobScore.user_id == user_id).all()
        ]
        q = self._db.query(JobPosting.id).filter(
            JobPosting.user_id == user_id,
            JobPosting.status != JobStatus.ARCHIVED.value,
        )
        if scored_ids:
            q = q.filter(~JobPosting.id.in_(scored_ids))
        rows = q.order_by(desc(JobPosting.date_found)).limit(limit).all()
        return [row[0] for row in rows]


class SQLAlchemyAgentRunRepository(AgentRunRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def create(self, run: AgentRun) -> AgentRun:
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return run

    def complete(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        output: dict,
        error_message: str | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> AgentRun:
        run = self._db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError("Agent run not found")
        run.status = status
        run.output = output
        run.error_message = error_message
        run.llm_provider = llm_provider
        run.llm_model = llm_model
        run.completed_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(run)
        return run

    def list_for_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> list[AgentRun]:
        return (
            self._db.query(AgentRun)
            .filter(AgentRun.user_id == user_id, AgentRun.job_id == job_id)
            .order_by(desc(AgentRun.started_at))
            .all()
        )
