from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "resumeuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "resumeuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_resume_labels(client, auth_headers):
    response = await client.get("/api/v1/resumes/labels", headers=auth_headers)
    assert response.status_code == 200
    labels = response.json()["labels"]
    assert "Production Resume" in labels
    assert "IT Resume" in labels
    assert len(labels) == 5


@pytest.mark.asyncio
async def test_upload_and_list_resumes(client, auth_headers):
    content = (FIXTURES / "production_resume.txt").read_bytes()
    upload = await client.post(
        "/api/v1/resumes/master",
        headers=auth_headers,
        data={"label": "Production Resume"},
        files={"file": ("production_resume.txt", content, "text/plain")},
    )
    assert upload.status_code == 201
    data = upload.json()
    assert data["label"] == "Production Resume"
    assert data["category"] == "production"
    assert data["version"] == 1

    listing = await client.get("/api/v1/resumes/master", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_upload_requires_auth(client):
    response = await client.get("/api/v1/resumes/master")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_resume_version_on_replace(client, auth_headers):
    content = (FIXTURES / "production_resume.txt").read_bytes()
    first = await client.post(
        "/api/v1/resumes/master",
        headers=auth_headers,
        data={"label": "IT Resume"},
        files={"file": ("it_v1.txt", content, "text/plain")},
    )
    resume_id = first.json()["id"]

    second = await client.post(
        "/api/v1/resumes/master",
        headers=auth_headers,
        data={"label": "IT Resume"},
        files={"file": ("it_v2.txt", content + b"\nupdated", "text/plain")},
    )
    assert second.json()["version"] == 2

    versions = await client.get(
        f"/api/v1/resumes/master/{resume_id}/versions",
        headers=auth_headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) == 1
