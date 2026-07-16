import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.domain.scheduler_enums import PipelineRunStatus, PipelineTrigger


@pytest.fixture
def mock_scheduler(client):
    from app.dependencies import get_scheduler_service
    from app.main import app

    mock = MagicMock()
    run_id = uuid.uuid4()
    mock_run = MagicMock()
    mock_run.id = run_id
    mock_run.trigger_type = PipelineTrigger.MANUAL.value
    mock_run.scope = "all"
    mock_run.scope_filter = {}
    mock_run.status = PipelineRunStatus.COMPLETED.value
    mock_run.step_log = [{"step": "search_jobs", "status": "completed"}]
    mock_run.summary = {"applications_ready_for_review": 1}
    mock_run.notification_sent = True
    mock_run.error_message = None
    mock_run.started_at = None
    mock_run.completed_at = None
    mock_run.created_at = datetime.now(timezone.utc)

    mock.run_manual.return_value = mock_run
    mock.run_for_source.return_value = mock_run
    mock.run_for_company.return_value = mock_run
    mock.run_for_job.return_value = mock_run
    mock.list_runs.return_value = [mock_run]
    mock.get_run.return_value = mock_run
    mock.scheduler_status.return_value = {
        "enabled": False,
        "running": False,
        "schedule_hour": 7,
        "schedule_minute": 0,
        "timezone": "America/Toronto",
        "next_run_at": None,
    }
    mock.list_notifications.return_value = []

    app.dependency_overrides[get_scheduler_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_scheduler_service, None)


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "scheduler@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "scheduler@example.com", "password": "testpass123"},
        )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_manual_pipeline_run(client, auth_headers, mock_scheduler):
    response = await client.post("/api/v1/scheduler/run", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == PipelineRunStatus.COMPLETED.value
    mock_scheduler.run_manual.assert_called_once()


@pytest.mark.asyncio
async def test_source_pipeline_run(client, auth_headers, mock_scheduler):
    source_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/scheduler/run/source/{source_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    mock_scheduler.run_for_source.assert_called_once()


@pytest.mark.asyncio
async def test_company_pipeline_run(client, auth_headers, mock_scheduler):
    response = await client.post(
        "/api/v1/scheduler/run/company",
        headers=auth_headers,
        json={"company": "Acme Corp"},
    )
    assert response.status_code == 200
    mock_scheduler.run_for_company.assert_called_once()


@pytest.mark.asyncio
async def test_job_pipeline_run(client, auth_headers, mock_scheduler):
    job_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/scheduler/run/job/{job_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    mock_scheduler.run_for_job.assert_called_once()


@pytest.mark.asyncio
async def test_scheduler_status(client, auth_headers, mock_scheduler):
    response = await client.get("/api/v1/scheduler/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["enabled"] is False
