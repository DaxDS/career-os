import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.services.application_tracking_service import ApplicationTrackingService
from app.domain.enums import ApplicationStatus, JobStatus, StorageCategory
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import JobApplication, JobPosting
from app.infrastructure.repositories.application_repository import SQLAlchemyApplicationRepository
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.config import Settings


@pytest.fixture
def tracking_setup(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    settings = Settings(storage_path=tmp_path / "storage")
    storage = LocalFileStorage(settings)
    app_repo = SQLAlchemyApplicationRepository(session)
    job_repo = SQLAlchemyJobRepository(session)
    service = ApplicationTrackingService(app_repo, job_repo, storage)

    user_id = uuid.uuid4()
    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Developer",
        company="Acme",
        description="Python role",
        description_hash="abc",
        dedup_key="def",
        status=JobStatus.DOCUMENTS_READY.value,
    )
    application = JobApplication(
        user_id=user_id,
        job_id=job.id,
        master_resume_id=uuid.uuid4(),
        status=ApplicationStatus.GENERATED.value,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.add(application)
    session.commit()

    yield service, user_id, job, application, session
    session.close()


def test_approve_and_submit_workflow(tracking_setup):
    service, user_id, job, application, _ = tracking_setup

    approved = service.approve(user_id, job.id, approved=True, notes="Looks good")
    assert approved.status == ApplicationStatus.APPROVED.value
    assert approved.approved_at is not None

    submitted = service.record_submission(
        user_id,
        job.id,
        submission_url="https://careers.acme.com/apply/123",
        submission_method="company_portal",
        notes="Submitted via portal",
    )
    assert submitted.status == ApplicationStatus.SUBMITTED.value
    assert submitted.submitted_at is not None
    assert submitted.submission_method == "company_portal"

    refreshed_job = service._jobs.get_posting_by_id(job.id, user_id)
    assert refreshed_job.status == JobStatus.APPLIED.value


def test_cannot_submit_without_approval(tracking_setup):
    service, user_id, job, *_ = tracking_setup

    with pytest.raises(ValueError, match="approved"):
        service.record_submission(user_id, job.id)


def test_upload_screenshot(tracking_setup):
    service, user_id, job, application, _ = tracking_setup

    screenshot = service.upload_screenshot(
        user_id,
        job.id,
        filename="confirmation.png",
        content=b"\x89PNG fake",
        caption="Application submitted",
    )
    assert screenshot.original_filename == "confirmation.png"
    assert screenshot.application_id == application.id

    tracking = service.get_tracking(user_id, job.id)
    assert len(tracking.screenshots) == 1


def test_list_applications_by_status(tracking_setup):
    service, user_id, job, *_ = tracking_setup

    service.approve(user_id, job.id)
    rows = service.list_applications(user_id, status=ApplicationStatus.APPROVED.value)
    assert len(rows) == 1
    assert rows[0][0].job_id == job.id
    assert rows[0][1].title == "Developer"


def test_withdraw_application(tracking_setup):
    service, user_id, job, *_ = tracking_setup
    service.approve(user_id, job.id)
    withdrawn = service.withdraw(user_id, job.id, notes="Role filled")
    assert withdrawn.status == ApplicationStatus.WITHDRAWN.value
