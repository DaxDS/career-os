import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.services.application_tracking_service import ApplicationTrackingService
from app.application.services.review_queue_service import ReviewQueueService
from app.domain.enums import ApplicationStatus, DocumentType, ReviewDecision
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    ApplicationDocument,
    JobApplication,
    JobPosting,
    JobScore,
)
from app.infrastructure.repositories.application_repository import SQLAlchemyApplicationRepository
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.infrastructure.repositories.score_repository import SQLAlchemyScoreRepository
from app.config import Settings
from app.infrastructure.storage.local_storage import LocalFileStorage


@pytest.fixture
def review_setup(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    settings = Settings(storage_path=tmp_path / "storage")
    app_repo = SQLAlchemyApplicationRepository(session)
    job_repo = SQLAlchemyJobRepository(session)
    score_repo = SQLAlchemyScoreRepository(session)
    tracking = ApplicationTrackingService(
        app_repo, job_repo, LocalFileStorage(settings)
    )
    service = ReviewQueueService(app_repo, score_repo, tracking)

    user_id = uuid.uuid4()
    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Developer",
        company="Acme",
        description="Python role",
        description_hash="abc",
        dedup_key="def",
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
    session.flush()
    session.add(
        JobScore(
            user_id=user_id,
            job_id=job.id,
            overall_score=85,
            match_score=80,
            scored_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        ApplicationDocument(
            application_id=application.id,
            document_type=DocumentType.TAILORED_RESUME.value,
            content={"summary": "Experienced Python developer"},
        )
    )
    session.add(
        ApplicationDocument(
            application_id=application.id,
            document_type=DocumentType.COVER_LETTER.value,
            content={"full_text": "Dear Hiring Manager, I am excited to apply."},
        )
    )
    session.commit()

    yield service, user_id, job, application, session
    session.close()


def test_queue_lists_generated_applications(review_setup):
    service, user_id, job, application, _ = review_setup
    queue = service.get_queue(user_id)
    assert len(queue) == 1
    assert queue[0].job_id == job.id
    assert queue[0].overall_score == 85
    assert "Python developer" in queue[0].resume_summary_preview


def test_approve_moves_to_approved(review_setup):
    service, user_id, job, *_ = review_setup
    result = service.decide(user_id, job.id, ReviewDecision.APPROVE, notes="Looks good")
    assert result.status == ApplicationStatus.APPROVED.value
    assert result.review_notes == "Looks good"


def test_reject_moves_to_rejected(review_setup):
    service, user_id, job, *_ = review_setup
    result = service.decide(user_id, job.id, ReviewDecision.REJECT, notes="Tone off")
    assert result.status == ApplicationStatus.REJECTED.value


def test_batch_approve(review_setup):
    service, user_id, job, *_ = review_setup
    results = service.batch_decide(user_id, [job.id], ReviewDecision.APPROVE)
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].status == ApplicationStatus.APPROVED.value


def test_stats(review_setup):
    service, user_id, *_ = review_setup
    stats = service.get_stats(user_id)
    assert stats["pending_review"] == 1
    assert stats["approved"] == 0
