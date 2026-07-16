import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "jobuser@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "jobuser@example.com", "password": "testpass123"},
        )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


@pytest.mark.asyncio
async def test_list_jobs_requires_auth(client):
    response = await client.get("/api/v1/jobs")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_builtin_source_presets(client):
    response = await client.get("/api/v1/jobs/sources/presets")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) == 5
    names = {p["name"] for p in presets}
    assert "Job Bank Canada" in names
    assert "Manual URL Import" in names


@pytest.mark.asyncio
async def test_builtin_sources_seeded_on_register(client, auth_headers):
    response = await client.get("/api/v1/jobs/sources", headers=auth_headers)
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) == 5
    assert all(s["is_builtin"] for s in sources)
    preset_keys = {s["preset_key"] for s in sources}
    assert "job_bank_canada" in preset_keys
    assert "manual_url_import" in preset_keys


@pytest.mark.asyncio
async def test_create_source_and_import_job(client, auth_headers, sample_job):
    sources = await client.get("/api/v1/jobs/sources", headers=auth_headers)
    source_id = next(
        s["id"] for s in sources.json() if s["preset_key"] == "job_bank_canada"
    )

    import_resp = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"source_id": source_id, "jobs": [sample_job]},
    )
    assert import_resp.status_code == 201
    data = import_resp.json()
    assert data["created"] == 1
    assert data["duplicates"] == 0
    assert data["results"][0]["import_status"] == "created"
    assert data["results"][0]["job"]["role_family"] == "production"

    list_resp = await client.get("/api/v1/jobs", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_import_detected(client, auth_headers, sample_job):
    await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    second = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    assert second.status_code == 201
    data = second.json()
    assert data["created"] == 0
    assert data["duplicates"] == 1
    assert data["results"][0]["match_reason"] == "external_id"


@pytest.mark.asyncio
async def test_get_and_archive_job(client, auth_headers, sample_job):
    imported = await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    job_id = imported.json()["results"][0]["job"]["id"]

    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == sample_job["title"]

    archive_resp = await client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert archive_resp.status_code == 200

    list_resp = await client.get("/api/v1/jobs", headers=auth_headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_filter_jobs_by_province(client, auth_headers, sample_job):
    await client.post(
        "/api/v1/jobs/import",
        headers=auth_headers,
        json={"jobs": [sample_job]},
    )
    pe = await client.get("/api/v1/jobs?province=PE", headers=auth_headers)
    on = await client.get("/api/v1/jobs?province=ON", headers=auth_headers)
    assert len(pe.json()) == 1
    assert len(on.json()) == 0
