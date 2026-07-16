import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


@pytest.fixture
def ai_disabled(client):
    """Force ai_enabled=False regardless of the ambient .env, so these tests
    are deterministic and never hit real LLM providers."""
    from app.config import get_settings
    from app.main import app

    settings = get_settings().model_copy(update={"ai_enabled": False})
    app.dependency_overrides[get_settings] = lambda: settings
    yield settings
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "aiuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "aiuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_ai_status(client, ai_disabled):
    response = await client.get("/api/v1/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ai_enabled"] is False
    assert "job_classification" in data["capabilities"]
    assert "openai" in data["providers"]


@pytest.mark.asyncio
async def test_classify_job_rule_based(client, auth_headers, ai_disabled):
    response = await client.post(
        "/api/v1/ai/jobs/classify",
        headers=auth_headers,
        json={
            "title": "Manufacturing Production Operator",
            "company": "Atlantic Foods",
            "description": "PLC monitoring and quality control in food plant",
        },
    )
    assert response.status_code == 200
    data = response.json()["classification"]
    assert data["role_family"] == "production"
    assert data["classification_method"] == "rule_based"


@pytest.mark.asyncio
async def test_prompt_sync_endpoint(client, auth_headers):
    response = await client.post("/api/v1/foundation/prompts/sync", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["synced"] >= 0


@pytest.mark.asyncio
async def test_score_job_requires_ai(client, auth_headers, sample_job, ai_disabled):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]

    response = await client.post(
        f"/api/v1/ai/jobs/{job_id}/score",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "disabled" in response.json()["detail"].lower()
