import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.application.services.scheduler_pipeline_service import SchedulerPipelineService
from app.domain.enums import ApplicationStatus, JobStatus
from app.domain.scheduler_enums import (
    REVIEW_READY_MESSAGE,
    PipelineRunStatus,
    PipelineScope,
    PipelineTrigger,
)
from app.infrastructure.db.models import JobApplication, JobPosting, JobSource
from app.infrastructure.db.scheduler_models import PipelineRun
from app.infrastructure.jobs.search.config_adapter import ConfigJobSearchAdapter


@pytest.fixture
def pipeline_service():
    job_service = MagicMock()
    job_repo = MagicMock()
    job_search = MagicMock()
    intelligence = MagicMock()
    documents = MagicMock()
    application_repo = MagicMock()
    score_repo = MagicMock()
    scheduler_repo = MagicMock()
    notifier = MagicMock()

    def create_run(run: PipelineRun) -> PipelineRun:
        run.id = uuid.uuid4()
        return run

    scheduler_repo.create_run.side_effect = create_run
    scheduler_repo.update_run.side_effect = lambda run: run

    return SchedulerPipelineService(
        job_service,
        job_repo,
        job_search,
        intelligence,
        documents,
        application_repo,
        score_repo,
        scheduler_repo,
        notifier,
    ), {
        "job_service": job_service,
        "job_repo": job_repo,
        "job_search": job_search,
        "intelligence": intelligence,
        "documents": documents,
        "application_repo": application_repo,
        "score_repo": score_repo,
        "scheduler_repo": scheduler_repo,
        "notifier": notifier,
    }


def test_config_job_search_reads_scheduled_jobs():
    source = JobSource(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Indeed",
        source_type="scraper",
        config={
            "scheduled_search_jobs": [
                {"title": "Engineer", "company": "Acme", "description": "Build things"},
            ]
        },
    )
    results = ConfigJobSearchAdapter().search(source)
    assert len(results) == 1
    assert results[0]["company"] == "Acme"


def test_manual_pipeline_imports_analyzes_and_notifies(pipeline_service):
    service, mocks = pipeline_service
    user_id = uuid.uuid4()
    source = JobSource(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Indeed",
        source_type="scraper",
        preset_key="indeed",
        config={},
        is_active=True,
    )
    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        source_id=source.id,
        title="Developer",
        company="Acme",
        description="Python",
        description_hash="h1",
        dedup_key="d1",
        status=JobStatus.NEW.value,
    )
    application = JobApplication(
        id=uuid.uuid4(),
        user_id=user_id,
        job_id=job.id,
        status=ApplicationStatus.GENERATED.value,
    )

    mocks["job_service"].list_sources.return_value = [source]
    mocks["job_search"].search_source.return_value = [
        {"title": "Developer", "company": "Acme", "description": "Python"}
    ]
    mocks["job_service"].import_jobs.return_value = [
        {"import_status": "created", "job": job},
    ]
    mocks["job_repo"].list_postings.return_value = [job]
    score = MagicMock()
    mocks["score_repo"].get_by_job.side_effect = [None, score]
    mocks["application_repo"].get_by_job.side_effect = [None, application]
    mocks["documents"].generate_documents.return_value = application

    run = service.run_pipeline(user_id, trigger=PipelineTrigger.MANUAL, scope=PipelineScope.ALL)

    assert run.status == PipelineRunStatus.COMPLETED.value
    mocks["intelligence"].analyze_job.assert_called_once()
    mocks["documents"].generate_documents.assert_called_once()
    mocks["notifier"].notify_user.assert_called_once_with(
        user_id,
        REVIEW_READY_MESSAGE,
        pipeline_run_id=run.id,
        details={"applications_ready_for_review": 1},
    )


def test_single_job_pipeline_skips_search(pipeline_service):
    service, mocks = pipeline_service
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = JobPosting(
        id=job_id,
        user_id=user_id,
        title="Developer",
        company="Acme",
        description="Python",
        description_hash="h1",
        dedup_key="d1",
        status=JobStatus.NEW.value,
    )
    mocks["job_service"].get_job.return_value = job
    mocks["score_repo"].get_by_job.return_value = MagicMock()
    mocks["application_repo"].get_by_job.return_value = None
    mocks["documents"].generate_documents.return_value = MagicMock(
        status=ApplicationStatus.GENERATED.value
    )

    run = service.run_pipeline(
        user_id,
        trigger=PipelineTrigger.MANUAL,
        scope=PipelineScope.JOB,
        job_id=job_id,
    )

    assert run.status == PipelineRunStatus.COMPLETED.value
    mocks["job_search"].search_source.assert_not_called()
    mocks["job_service"].import_jobs.assert_not_called()
    step_names = [entry["step"] for entry in run.step_log]
    assert step_names[0] == "search_jobs"
    assert run.step_log[0]["status"] == "skipped"


def test_pipeline_skips_notification_when_nothing_ready(pipeline_service):
    service, mocks = pipeline_service
    user_id = uuid.uuid4()
    mocks["job_service"].list_sources.return_value = []
    mocks["job_repo"].list_postings.return_value = []

    run = service.run_pipeline(user_id, trigger=PipelineTrigger.MANUAL, scope=PipelineScope.ALL)

    assert run.status == PipelineRunStatus.COMPLETED.value
    assert run.notification_sent is False
    mocks["notifier"].notify_user.assert_not_called()
