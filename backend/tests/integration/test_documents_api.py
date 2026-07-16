import json
from pathlib import Path
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timezone

import pytest

from app.infrastructure.db.models import ApplicationDocument, JobApplication

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "docuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "docuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


@pytest.fixture
def mock_doc_service(client):
    from app.dependencies import get_document_generation_service
    from app.main import app

    mock = MagicMock()
    app_id = uuid.uuid4()
    job_id_holder: dict = {}

    def generate(user_id, job_id, force=False):
        job_id_holder["id"] = job_id
        application = JobApplication(
            id=app_id,
            user_id=user_id,
            job_id=job_id,
            master_resume_id=uuid.uuid4(),
            status="generated",
            version=1,
            ats_fact_check_passed=True,
            generation_metadata={},
            generated_at=datetime.now(timezone.utc),
        )
        application.documents = [
            ApplicationDocument(
                id=uuid.uuid4(),
                application_id=app_id,
                document_type="tailored_resume",
                file_path="/tmp/TailoredResume.json",
                content={"summary": "Tailored"},
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        return application

    mock.generate_documents.side_effect = generate
    mock.get_application.side_effect = generate
    mock.get_document.side_effect = lambda uid, jid, dtype: generate(uid, jid).documents[0]

    app.dependency_overrides[get_document_generation_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_document_generation_service, None)


@pytest.mark.asyncio
async def test_generate_documents_endpoint(client, auth_headers, sample_job, mock_doc_service):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]

    response = await client.post(
        f"/api/v1/documents/jobs/{job_id}/generate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["application"]["job_id"] == job_id
    assert data["application"]["ats_fact_check_passed"] is True
    mock_doc_service.generate_documents.assert_called_once()


@pytest.mark.asyncio
async def test_get_application_documents(client, auth_headers, sample_job, mock_doc_service):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]
    await client.post(f"/api/v1/documents/jobs/{job_id}/generate", headers=auth_headers)

    response = await client.get(
        f"/api/v1/documents/jobs/{job_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "generated"
