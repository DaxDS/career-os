import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_automation(client):
    from app.dependencies import get_application_automation_service
    from app.main import app

    mock = MagicMock()
    mock.start_submission = AsyncMock(
        return_value={
            "run_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "status": "stopped_before_submit",
            "submitted": False,
            "connector_key": "job_bank_canada",
            "browser": "chromium",
            "paused_for_captcha": False,
            "result": {},
        }
    )
    mock.list_sessions.return_value = []

    app.dependency_overrides[get_application_automation_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_application_automation_service, None)


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "autouser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "autouser@example.com", "password": "testpass123"},
        )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_start_automation_endpoint(client, auth_headers, mock_automation):
    job_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/automation/jobs/{job_id}/submit",
        headers=auth_headers,
        json={"stop_before_submit": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped_before_submit"
    assert data["connector_key"] == "job_bank_canada"


@pytest.mark.asyncio
async def test_list_sessions_endpoint(client, auth_headers, mock_automation):
    response = await client.get("/api/v1/automation/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
