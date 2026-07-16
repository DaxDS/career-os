import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.services.document_generation_service import DocumentGenerationService
from app.config import Settings
from app.domain.enums import ApplicationStatus, DocumentType, JobStatus
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import JobPosting, JobScore, MasterResume, UserProfile
from app.infrastructure.repositories.application_repository import SQLAlchemyApplicationRepository
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.infrastructure.repositories.score_repository import SQLAlchemyScoreRepository
from app.infrastructure.storage.local_storage import LocalFileStorage


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session, tmp_path
    session.close()


@pytest.fixture
def doc_service(db_session):
    session, tmp_path = db_session
    settings = Settings(ai_enabled=True, storage_path=tmp_path / "storage")

    job_repo = SQLAlchemyJobRepository(session)
    score_repo = SQLAlchemyScoreRepository(session)
    app_repo = SQLAlchemyApplicationRepository(session)
    user_repo = MagicMock()
    resume_repo = MagicMock()
    tailoring = MagicMock()
    ats = MagicMock()
    cover = MagicMock()
    email = MagicMock()

    return (
        DocumentGenerationService(
            job_repo,
            user_repo,
            resume_repo,
            score_repo,
            app_repo,
            LocalFileStorage(settings),
            tailoring,
            ats,
            cover,
            email,
            settings,
        ),
        session,
        user_repo,
        resume_repo,
        tailoring,
        ats,
        cover,
        email,
    )


def _seed_job_context(session, user_repo, resume_repo):
    user_id = uuid.uuid4()
    profile = UserProfile(user_id=user_id, legal_name="Jane Doe")
    user_repo.get_profile.return_value = profile

    master = MasterResume(
        id=uuid.uuid4(),
        user_id=user_id,
        label="IT Resume",
        category="it",
        file_path="/tmp/resume.pdf",
        original_filename="resume.pdf",
        parsed_content={"summary": "Engineer", "skills": ["Python"]},
    )
    resume_repo.get_master_by_id.return_value = master

    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Developer",
        company="Acme",
        description="Python developer",
        description_hash="abc",
        dedup_key="def",
        status=JobStatus.SCORED.value,
        classification={"required_skills": ["Python", "FastAPI"]},
    )
    session.add(job)
    session.add(
        JobScore(
            user_id=user_id,
            job_id=job.id,
            overall_score=80,
            selected_master_resume_id=master.id,
            scored_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    return user_id, job, master


def test_generate_persists_documents_and_artifacts(doc_service):
    service, session, user_repo, resume_repo, tailoring, ats, cover, email = doc_service
    user_id, job, master = _seed_job_context(session, user_repo, resume_repo)

    tailoring.tailor.return_value = {"summary": "Tailored engineer", "skills": ["Python"]}
    ats.analyze_post_tailor.return_value = {
        "ats_score": 85,
        "fact_check": {"passed": True},
        "invented_entities": [],
    }
    cover.generate.return_value = {"full_text": "Dear Hiring Manager..."}
    email.generate.return_value = {"subject": "Application", "body_text": "Hello"}

    application = service.generate_documents(user_id, job.id)

    assert application.status == ApplicationStatus.GENERATED.value
    assert application.ats_fact_check_passed is True
    assert len(application.documents) == 4
    assert job.status == JobStatus.DOCUMENTS_READY.value

    doc_types = {d.document_type for d in application.documents}
    assert doc_types == {
        DocumentType.TAILORED_RESUME.value,
        DocumentType.COVER_LETTER.value,
        DocumentType.EMAIL.value,
        DocumentType.ATS_REPORT.value,
    }
    for doc in application.documents:
        assert doc.file_path


def test_generate_requires_layer5_scores(doc_service):
    service, session, user_repo, resume_repo, *_ = doc_service
    user_id = uuid.uuid4()
    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Developer",
        company="Acme",
        description="desc",
        description_hash="h",
        dedup_key="k",
    )
    session.add(job)
    session.commit()

    with pytest.raises(ValueError, match="analyzed first"):
        service.generate_documents(user_id, job.id)


def test_returns_existing_without_force(doc_service):
    service, session, user_repo, resume_repo, tailoring, ats, cover, email = doc_service
    user_id, job, master = _seed_job_context(session, user_repo, resume_repo)

    tailoring.tailor.return_value = {"summary": "v1"}
    ats.analyze_post_tailor.return_value = {"fact_check": {"passed": True}}
    cover.generate.return_value = {"full_text": "letter"}
    email.generate.return_value = {"body_text": "email"}

    first = service.generate_documents(user_id, job.id)
    second = service.generate_documents(user_id, job.id)

    assert first.id == second.id
    assert tailoring.tailor.call_count == 1
