import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db import scheduler_models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.scheduler_models import PipelineNotification, PipelineRun
from app.infrastructure.repositories.scheduler_repository import SQLAlchemyPipelineRunRepository


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


def test_scheduler_repository_crud(db_session):
    repo = SQLAlchemyPipelineRunRepository(db_session)
    user_id = uuid.uuid4()
    run = PipelineRun(
        user_id=user_id,
        trigger_type="manual",
        scope="all",
        scope_filter={},
        status="completed",
        step_log=[],
        summary={},
        started_at=datetime.now(timezone.utc),
    )
    created = repo.create_run(run)
    fetched = repo.get_run(user_id, created.id)
    assert fetched is not None
    assert fetched.trigger_type == "manual"

    notification = PipelineNotification(
        user_id=user_id,
        pipeline_run_id=created.id,
        message="Today's applications are ready for review.",
        details={"applications_ready_for_review": 2},
    )
    repo.create_notification(notification)
    notifications = repo.list_notifications(user_id)
    assert len(notifications) == 1
    assert notifications[0].read_at is None

    marked = repo.mark_notification_read(user_id, notifications[0].id)
    assert marked is not None
    assert marked.read_at is not None
