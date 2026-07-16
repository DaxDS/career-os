import uuid
from datetime import datetime, timezone
from typing import Any

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.notification import NotificationPort
from app.application.ports.scheduler_repository import PipelineRunRepositoryPort
from app.application.ports.score_repository import ScoreRepositoryPort
from app.application.services.document_generation_service import DocumentGenerationService
from app.application.services.job_intelligence_service import JobIntelligenceService
from app.application.services.job_service import JobService
from app.domain.enums import ApplicationStatus, WorkflowType
from app.domain.scheduler_enums import (
    REVIEW_READY_MESSAGE,
    PipelineRunStatus,
    PipelineScope,
    PipelineStep,
    PipelineTrigger,
)
from app.infrastructure.db.models import JobPosting, JobSource
from app.infrastructure.db.scheduler_models import PipelineRun
from app.infrastructure.jobs.search.registry import JobSearchRegistry
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class SchedulerPipelineService:
    """Orchestrates the Layer 10 morning pipeline without auto-submitting applications."""

    def __init__(
        self,
        job_service: JobService,
        job_repo: JobRepositoryPort,
        job_search: JobSearchRegistry,
        intelligence: JobIntelligenceService,
        documents: DocumentGenerationService,
        application_repo: ApplicationRepositoryPort,
        score_repo: ScoreRepositoryPort,
        scheduler_repo: PipelineRunRepositoryPort,
        notifier: NotificationPort,
    ):
        self._jobs = job_service
        self._job_repo = job_repo
        self._search = job_search
        self._intelligence = intelligence
        self._documents = documents
        self._applications = application_repo
        self._scores = score_repo
        self._scheduler_repo = scheduler_repo
        self._notifier = notifier

    def run_pipeline(
        self,
        user_id: uuid.UUID,
        *,
        trigger: PipelineTrigger,
        scope: PipelineScope,
        source_id: uuid.UUID | None = None,
        company: str | None = None,
        job_id: uuid.UUID | None = None,
    ) -> PipelineRun:
        scope_filter = self._build_scope_filter(source_id=source_id, company=company, job_id=job_id)
        run = PipelineRun(
            user_id=user_id,
            trigger_type=trigger.value,
            scope=scope.value,
            scope_filter=scope_filter,
            status=PipelineRunStatus.RUNNING.value,
            step_log=[],
            summary={},
            notification_sent=False,
            started_at=datetime.now(timezone.utc),
        )
        run = self._scheduler_repo.create_run(run)

        try:
            summary: dict[str, Any] = {
                "jobs_searched": 0,
                "jobs_imported_created": 0,
                "jobs_imported_duplicates": 0,
                "jobs_analyzed": 0,
                "jobs_documents_generated": 0,
                "applications_ready_for_review": 0,
                "errors": [],
            }
            pipeline_errors: list[str] = []

            if scope != PipelineScope.JOB:
                search_stats = self._step_search_and_import(user_id, run, source_id, scope)
                summary.update(search_stats)
            else:
                self._append_step(
                    run,
                    PipelineStep.SEARCH_JOBS,
                    {"status": "skipped", "reason": "single_job_scope"},
                )
                self._append_step(
                    run,
                    PipelineStep.IMPORT_JOBS,
                    {"status": "skipped", "reason": "single_job_scope"},
                )

            target_jobs = self._jobs_in_scope(user_id, scope, source_id, company, job_id)
            intelligence_stats = self._step_intelligence(user_id, run, target_jobs, pipeline_errors)
            summary.update(intelligence_stats)

            document_stats = self._step_documents(user_id, run, target_jobs, pipeline_errors)
            summary.update(document_stats)

            review_count = self._step_review_queue(user_id, run, target_jobs)
            summary["applications_ready_for_review"] = review_count

            if review_count > 0:
                self._step_notify(user_id, run, summary)
                run.notification_sent = True
            else:
                run.notification_sent = False
                self._append_step(
                    run,
                    PipelineStep.NOTIFY_USER,
                    {"status": "skipped", "reason": "no_applications_ready"},
                )

            run.summary = summary
            run.status = PipelineRunStatus.COMPLETED.value
            run.completed_at = datetime.now(timezone.utc)
            run = self._scheduler_repo.update_run(run)
            logger.info("pipeline_completed", run_id=str(run.id), **summary)
            return run
        except Exception as exc:
            run.status = PipelineRunStatus.FAILED.value
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            self._scheduler_repo.update_run(run)
            logger.exception("pipeline_failed", run_id=str(run.id), error=str(exc))
            raise

    def _step_search_and_import(
        self,
        user_id: uuid.UUID,
        run: PipelineRun,
        source_id: uuid.UUID | None,
        scope: PipelineScope,
    ) -> dict[str, Any]:
        sources = self._active_sources(user_id, source_id)
        sources = [s for s in sources if s.preset_key != "manual_url_import"]
        all_found: list[dict[str, Any]] = []
        search_by_source: list[tuple[JobSource, list[dict[str, Any]]]] = []
        for source in sources:
            found = self._search.search_source(source)
            search_by_source.append((source, found))
            all_found.extend(found)

        self._append_step(
            run,
            PipelineStep.SEARCH_JOBS,
            {"status": "completed", "sources_searched": len(sources), "jobs_found": len(all_found)},
        )

        created = 0
        duplicates = 0
        for source, found in search_by_source:
            if not found:
                continue
            results = self._jobs.import_jobs(user_id, found, source_id=source.id)
            created += sum(1 for r in results if r["import_status"] == "created")
            duplicates += sum(1 for r in results if r["import_status"] == "duplicate")

        self._append_step(
            run,
            PipelineStep.IMPORT_JOBS,
            {"status": "completed", "created": created, "duplicates": duplicates},
        )
        self._append_step(
            run,
            PipelineStep.DEDUPLICATE,
            {"status": "completed", "duplicates": duplicates, "note": "applied during import"},
        )
        self._append_step(
            run,
            PipelineStep.CLASSIFICATION,
            {"status": "completed", "note": "applied during import"},
        )

        return {
            "jobs_searched": len(all_found),
            "jobs_imported_created": created,
            "jobs_imported_duplicates": duplicates,
        }

    def _step_intelligence(
        self,
        user_id: uuid.UUID,
        run: PipelineRun,
        target_jobs: list[JobPosting],
        errors: list[str],
    ) -> dict[str, Any]:
        analyzed = 0
        skipped = 0
        for job in target_jobs:
            job = self._jobs.enrich_description(user_id, job.id)
            existing = self._scores.get_by_job(user_id, job.id)
            if existing and not self._should_rescore(job, existing):
                continue
            if not self._jobs.has_scorable_description(job):
                skipped += 1
                msg = (
                    f"skipped scoring for {job.title} at {job.company}: "
                    "job description unavailable (Job Bank may be in maintenance)"
                )
                errors.append(msg)
                logger.warning("pipeline_scoring_skipped", job_id=str(job.id), title=job.title)
                continue
            try:
                self._intelligence.analyze_job(
                    user_id, job.id, workflow_type=WorkflowType.BATCH_INTELLIGENCE
                )
                analyzed += 1
            except Exception as exc:
                msg = f"intelligence failed for job {job.id}: {exc}"
                errors.append(msg)
                logger.warning("pipeline_intelligence_failed", job_id=str(job.id), error=str(exc))

        self._append_step(
            run,
            PipelineStep.IMMIGRATION_SCORING,
            {
                "status": "completed",
                "jobs_processed": analyzed,
                "jobs_skipped": skipped,
                "failures": len(errors),
            },
        )
        self._append_step(
            run,
            PipelineStep.ATS_ANALYSIS,
            {"status": "completed", "jobs_processed": analyzed, "note": "included in intelligence"},
        )
        self._append_step(
            run,
            PipelineStep.RESUME_SELECTION,
            {"status": "completed", "jobs_processed": analyzed, "note": "included in intelligence"},
        )
        return {"jobs_analyzed": analyzed, "errors": errors}

    @staticmethod
    def _should_rescore(job: JobPosting, score) -> bool:
        """Re-score when a prior run stored 0 because the description was missing."""
        if score.overall_score not in (0, None):
            return False
        return len((job.description or "").strip()) >= 80

    def _step_documents(
        self,
        user_id: uuid.UUID,
        run: PipelineRun,
        target_jobs: list[JobPosting],
        errors: list[str],
    ) -> dict[str, Any]:
        generated = 0
        for job in target_jobs:
            if not self._scores.get_by_job(user_id, job.id):
                continue
            existing = self._applications.get_by_job(user_id, job.id)
            if existing:
                continue
            try:
                self._documents.generate_documents(user_id, job.id)
                generated += 1
            except Exception as exc:
                msg = f"document generation failed for job {job.id}: {exc}"
                errors.append(msg)
                logger.warning("pipeline_documents_failed", job_id=str(job.id), error=str(exc))

        self._append_step(
            run,
            PipelineStep.RESUME_TAILORING,
            {"status": "completed", "jobs_processed": generated},
        )
        self._append_step(
            run,
            PipelineStep.COVER_LETTER,
            {"status": "completed", "jobs_processed": generated, "note": "included in documents"},
        )
        self._append_step(
            run,
            PipelineStep.RECRUITER_EMAIL,
            {"status": "completed", "jobs_processed": generated, "note": "included in documents"},
        )
        self._append_step(
            run,
            PipelineStep.APPLICATION_PACKAGE,
            {"status": "completed", "jobs_processed": generated},
        )
        return {"jobs_documents_generated": generated, "errors": errors}

    def _step_review_queue(
        self, user_id: uuid.UUID, run: PipelineRun, target_jobs: list[JobPosting]
    ) -> int:
        ready = 0
        for job in target_jobs:
            application = self._applications.get_by_job(user_id, job.id)
            if application and application.status == ApplicationStatus.GENERATED.value:
                ready += 1
        self._append_step(
            run,
            PipelineStep.REVIEW_QUEUE,
            {"status": "completed", "applications_ready": ready},
        )
        return ready

    def _step_notify(self, user_id: uuid.UUID, run: PipelineRun, summary: dict[str, Any]) -> None:
        self._notifier.notify_user(
            user_id,
            REVIEW_READY_MESSAGE,
            pipeline_run_id=run.id,
            details={"applications_ready_for_review": summary.get("applications_ready_for_review", 0)},
        )
        self._append_step(
            run,
            PipelineStep.NOTIFY_USER,
            {"status": "completed", "message": REVIEW_READY_MESSAGE},
        )

    def _active_sources(
        self, user_id: uuid.UUID, source_id: uuid.UUID | None
    ) -> list[JobSource]:
        if source_id:
            source = self._job_repo.get_source_by_id(source_id, user_id)
            if not source:
                raise ValueError("Job source not found")
            return [source] if source.is_active else []
        return [s for s in self._jobs.list_sources(user_id) if s.is_active]

    def _jobs_in_scope(
        self,
        user_id: uuid.UUID,
        scope: PipelineScope,
        source_id: uuid.UUID | None,
        company: str | None,
        job_id: uuid.UUID | None,
    ) -> list[JobPosting]:
        if scope == PipelineScope.JOB:
            if not job_id:
                raise ValueError("job_id is required for single-job pipeline runs")
            return [self._jobs.get_job(user_id, job_id)]

        jobs = self._job_repo.list_postings(user_id, exclude_archived=True)
        if scope == PipelineScope.SOURCE and source_id:
            jobs = [j for j in jobs if j.source_id == source_id]
        elif scope == PipelineScope.COMPANY:
            if company:
                company_lower = company.strip().lower()
                jobs = [j for j in jobs if (j.company or "").strip().lower() == company_lower]
            if source_id:
                jobs = [j for j in jobs if j.source_id == source_id]
        return jobs

    @staticmethod
    def _build_scope_filter(
        *,
        source_id: uuid.UUID | None,
        company: str | None,
        job_id: uuid.UUID | None,
    ) -> dict[str, str]:
        scope_filter: dict[str, str] = {}
        if source_id:
            scope_filter["source_id"] = str(source_id)
        if company:
            scope_filter["company"] = company
        if job_id:
            scope_filter["job_id"] = str(job_id)
        return scope_filter

    @staticmethod
    def _append_step(run: PipelineRun, step: PipelineStep, details: dict[str, Any]) -> None:
        entry = {"step": step.value, **details}
        run.step_log = [*run.step_log, entry]
