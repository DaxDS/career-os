import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.v1_constants import CURRENT_LAYER
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == CURRENT_LAYER
    assert data["app"] == "Career OS"


@pytest.mark.asyncio
async def test_openapi_available(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Career OS"
