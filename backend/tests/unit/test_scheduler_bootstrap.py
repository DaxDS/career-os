import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.services.scheduler_pipeline_service import SchedulerPipelineService
from app.dependencies import _build_scheduler_pipeline_service
from app.infrastructure.db import automation_models  # noqa: F401
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db import scheduler_models  # noqa: F401
from app.infrastructure.db.base import Base


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


def test_build_scheduler_pipeline_service_wires_dependencies(db_session):
    service = _build_scheduler_pipeline_service(db_session)
    assert isinstance(service, SchedulerPipelineService)
