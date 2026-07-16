import json
from pathlib import Path
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timezone

import pytest

from app.infrastructure.db.models import JobScore

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "agentuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "agentuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


@pytest.fixture
def mock_intelligence(client):
    from app.dependencies import get_job_intelligence_service
    from app.main import app

    mock = MagicMock()
    job_id_holder = {}

    def analyze(user_id, job_id, workflow_type=None):
        job_id_holder["id"] = job_id
        return JobScore(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=job_id,
            ats_score=80,
            match_score=85,
            immigration_score=70,
            pr_score=75,
            overall_score=82,
            immigration_details={},
            ats_details={},
            match_details={},
            selection_details={"selected_resume_id": str(uuid.uuid4())},
            scoring_method="llm",
            agent_metadata={},
            scored_at=datetime.now(timezone.utc),
        )

    mock.analyze_job.side_effect = analyze
    mock.get_scores.side_effect = lambda uid, jid: analyze(uid, jid)
    mock.list_ranked.return_value = []
    mock.batch_analyze.return_value = []

    app.dependency_overrides[get_job_intelligence_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_job_intelligence_service, None)


@pytest.mark.asyncio
async def test_analyze_job_endpoint(client, auth_headers, sample_job, mock_intelligence):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]

    response = await client.post(
        f"/api/v1/agents/jobs/{job_id}/analyze",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 82
    assert data["job_id"] == job_id
    mock_intelligence.analyze_job.assert_called_once()


@pytest.mark.asyncio
async def test_get_persisted_scores(client, auth_headers, sample_job, mock_intelligence):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]
    await client.post(f"/api/v1/agents/jobs/{job_id}/analyze", headers=auth_headers)

    response = await client.get(
        f"/api/v1/agents/jobs/{job_id}/scores",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["match_score"] == 85
