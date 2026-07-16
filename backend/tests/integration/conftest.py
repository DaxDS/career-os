import os

os.environ.setdefault("SCHEDULER_ENABLED", "false")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db
from app.infrastructure.db import models  # noqa: F401 — register tables
from app.infrastructure.db import automation_models  # noqa: F401 — Layer 9 tables
from app.infrastructure.db import scheduler_models  # noqa: F401 — Layer 10 tables
from app.infrastructure.db.base import Base
from app.main import app


@pytest.fixture
def test_db_session():
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
async def client(test_db_session):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
