import uuid

from app.application.services.scheduler_pipeline_service import SchedulerPipelineService
from app.domain.scheduler_enums import PipelineScope, PipelineTrigger
from app.infrastructure.db.scheduler_models import PipelineNotification, PipelineRun
from app.infrastructure.scheduler.apscheduler_runner import SchedulerRunner


class SchedulerService:
    """Facade for manual, scoped, and scheduled pipeline runs."""

    def __init__(
        self,
        pipeline: SchedulerPipelineService,
        scheduler_repo,
        runner: SchedulerRunner | None = None,
    ):
        self._pipeline = pipeline
        self._repo = scheduler_repo
        self._runner = runner

    def run_manual(self, user_id: uuid.UUID) -> PipelineRun:
        return self._pipeline.run_pipeline(
            user_id,
            trigger=PipelineTrigger.MANUAL,
            scope=PipelineScope.ALL,
        )

    def run_for_source(self, user_id: uuid.UUID, source_id: uuid.UUID) -> PipelineRun:
        return self._pipeline.run_pipeline(
            user_id,
            trigger=PipelineTrigger.MANUAL,
            scope=PipelineScope.SOURCE,
            source_id=source_id,
        )

    def run_for_company(
        self,
        user_id: uuid.UUID,
        company: str,
        *,
        source_id: uuid.UUID | None = None,
    ) -> PipelineRun:
        return self._pipeline.run_pipeline(
            user_id,
            trigger=PipelineTrigger.MANUAL,
            scope=PipelineScope.COMPANY,
            source_id=source_id,
            company=company,
        )

    def run_for_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> PipelineRun:
        return self._pipeline.run_pipeline(
            user_id,
            trigger=PipelineTrigger.MANUAL,
            scope=PipelineScope.JOB,
            job_id=job_id,
        )

    def run_scheduled(self, user_id: uuid.UUID) -> PipelineRun:
        return self._pipeline.run_pipeline(
            user_id,
            trigger=PipelineTrigger.SCHEDULED,
            scope=PipelineScope.ALL,
        )

    def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> PipelineRun | None:
        return self._repo.get_run(user_id, run_id)

    def list_runs(self, user_id: uuid.UUID, *, limit: int = 20) -> list[PipelineRun]:
        return self._repo.list_runs(user_id, limit=limit)

    def list_notifications(
        self, user_id: uuid.UUID, *, limit: int = 10, unread_only: bool = False
    ) -> list[PipelineNotification]:
        return self._repo.list_notifications(user_id, limit=limit, unread_only=unread_only)

    def mark_notification_read(
        self, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> PipelineNotification | None:
        return self._repo.mark_notification_read(user_id, notification_id)

    def scheduler_status(self) -> dict:
        if not self._runner:
            return {"enabled": False, "running": False, "next_run_at": None}
        return self._runner.status()
