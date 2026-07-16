import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.dependencies import get_db
from app.infrastructure.db.session import SessionLocal
from app.main import app


@pytest.fixture
def db_available():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readiness_endpoint(db_available):
    if not db_available:
        pytest.skip("PostgreSQL not available — start with docker compose up db")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


@pytest.mark.integration
def test_system_metadata_migration(db_available):
    if not db_available:
        pytest.skip("PostgreSQL not available — run alembic upgrade head first")

    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT key, value FROM system_metadata WHERE key = 'schema_layer'")
        ).fetchone()
        assert result is not None
        assert result[1] == "0"
    finally:
        db.close()
