import json
from pathlib import Path
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timezone

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "reviewuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "reviewuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


@pytest.fixture
def mock_review(client):
    from app.dependencies import get_review_queue_service
    from app.main import app

    mock = MagicMock()

    def queue_item():
        from app.application.services.review_queue_service import ReviewQueueItem

        return ReviewQueueItem(
            application_id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            title="Developer",
            company="Acme",
            location_province="ON",
            overall_score=80,
            ats_fact_check_passed=True,
            resume_summary_preview="Summary",
            cover_letter_preview="Dear Hiring Manager",
            generated_at=datetime.now(timezone.utc),
            version=1,
        )

    mock.get_queue.return_value = [queue_item()]
    mock.get_stats.return_value = {
        "pending_review": 1,
        "revision_requested": 0,
        "rejected": 0,
        "approved": 0,
    }
    mock.batch_decide.return_value = []

    app.dependency_overrides[get_review_queue_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_review_queue_service, None)


@pytest.mark.asyncio
async def test_review_queue_endpoint(client, auth_headers, mock_review):
    response = await client.get("/api/v1/review/queue", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["overall_score"] == 80


@pytest.mark.asyncio
async def test_review_stats_endpoint(client, auth_headers, mock_review):
    response = await client.get("/api/v1/review/stats", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pending_review"] == 1
