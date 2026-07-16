import json
from pathlib import Path
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timezone

import pytest

from app.infrastructure.db.models import ApplicationScreenshot, JobApplication

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "trackuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "trackuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


@pytest.fixture
def mock_tracking(client):
    from app.dependencies import get_application_tracking_service
    from app.main import app

    mock = MagicMock()
    app_id = uuid.uuid4()

    def make_application(user_id, job_id, status="generated"):
        now = datetime.now(timezone.utc)
        application = JobApplication(
            id=app_id,
            user_id=user_id,
            job_id=job_id,
            master_resume_id=uuid.uuid4(),
            status=status,
            version=1,
            ats_fact_check_passed=True,
            generation_metadata={},
            generated_at=now,
            approved_at=now if status == "approved" else None,
            submitted_at=now if status == "submitted" else None,
            submission_url="https://example.com/apply" if status == "submitted" else "",
            submission_method="company_portal" if status == "submitted" else None,
            submission_notes="",
            review_notes="",
            reviewed_at=None,
            screenshots=[],
        )
        return application

    def approve(user_id, job_id, approved=True, notes=""):
        return make_application(user_id, job_id, status="approved" if approved else "generated")

    def submit(user_id, job_id, **kwargs):
        app = make_application(user_id, job_id, status="submitted")
        app.submitted_at = datetime.now(timezone.utc)
        app.submission_method = kwargs.get("submission_method", "manual")
        return app

    mock.get_tracking.side_effect = lambda uid, jid: make_application(uid, jid)
    mock.approve.side_effect = approve
    mock.record_submission.side_effect = submit
    mock.list_applications.return_value = []

    app.dependency_overrides[get_application_tracking_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_application_tracking_service, None)


@pytest.mark.asyncio
async def test_approve_endpoint(client, auth_headers, sample_job, mock_tracking):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]

    response = await client.post(
        f"/api/v1/tracking/jobs/{job_id}/approve",
        headers=auth_headers,
        json={"approved": True, "notes": "Ready to send"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    mock_tracking.approve.assert_called_once()


@pytest.mark.asyncio
async def test_submit_endpoint(client, auth_headers, sample_job, mock_tracking):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]

    response = await client.post(
        f"/api/v1/tracking/jobs/{job_id}/submit",
        headers=auth_headers,
        json={
            "submission_url": "https://example.com/apply",
            "submission_method": "company_portal",
            "success": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
