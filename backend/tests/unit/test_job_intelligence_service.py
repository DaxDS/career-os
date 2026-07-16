import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.services.job_intelligence_service import JobIntelligenceService, IntelligenceState
from app.config import Settings
from app.domain.enums import JobStatus
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import JobPosting, JobScore
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.infrastructure.repositories.score_repository import SQLAlchemyScoreRepository


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def intelligence_service(db_session):
    job_repo = SQLAlchemyJobRepository(db_session)
    score_repo = SQLAlchemyScoreRepository(db_session)
    user_repo = MagicMock()
    resume_repo = MagicMock()
    immigration = MagicMock()
    scoring = MagicMock()
    ats = MagicMock()
    selection = MagicMock()

    return JobIntelligenceService(
        job_repo,
        user_repo,
        resume_repo,
        score_repo,
        immigration,
        scoring,
        ats,
        selection,
        Settings(ai_enabled=True),
    )


def test_persist_merges_agent_outputs(db_session, intelligence_service):
    user_id = uuid.uuid4()
    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Developer",
        company="Acme",
        description="Python developer role",
        description_hash="abc",
        dedup_key="def",
        status=JobStatus.NEW.value,
    )
    db_session.add(job)
    db_session.commit()

    state: IntelligenceState = {
        "user_id": str(user_id),
        "job_id": str(job.id),
        "immigration": {"immigration_score": 80, "noc_code": "21232"},
        "scoring": {
            "ats_score": 70,
            "match_score": 85,
            "pr_score": 75,
            "overall_score": 78,
            "rationale": "Good fit",
        },
        "ats": {"ats_score": 72, "missing_keywords": ["kubernetes"]},
        "selection": {
            "selected_resume_id": str(uuid.uuid4()),
            "confidence": 0.9,
            "rationale": "IT resume best match",
        },
        "errors": [],
    }

    score = intelligence_service._persist_from_state(user_id, job, state)
    assert score.overall_score == 78
    assert score.immigration_score == 80
    assert score.ats_score == 70
    assert score.match_score == 85
    assert score.selection_details["confidence"] == 0.9
    assert job.status == JobStatus.SCORED.value


def test_list_unscored_jobs(db_session):
    user_id = uuid.uuid4()
    job_repo = SQLAlchemyJobRepository(db_session)
    score_repo = SQLAlchemyScoreRepository(db_session)
    job1 = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="A",
        company="Co",
        description="d",
        description_hash="h1",
        dedup_key="k1",
    )
    job2 = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        title="B",
        company="Co",
        description="d",
        description_hash="h2",
        dedup_key="k2",
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    unscored = score_repo.list_unscored_job_ids(user_id)
    assert len(unscored) == 2

    score_repo.upsert(
        JobScore(
            user_id=user_id,
            job_id=job1.id,
            overall_score=90,
            scored_at=datetime.now(timezone.utc),
        )
    )
    unscored = score_repo.list_unscored_job_ids(user_id)
    assert unscored == [job2.id]
