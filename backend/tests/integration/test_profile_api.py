import pytest


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "apitest@example.com", "password": "testpass123"},
    )
    if response.status_code == 400:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "apitest@example.com", "password": "testpass123"},
        )
    assert response.status_code in (200, 201), response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_and_login(client):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "securepass1"},
    )
    assert reg.status_code == 201
    assert "access_token" in reg.json()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "newuser@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_blocked_in_single_user_mode(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "password": "securepass1"},
    )
    second = await client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "securepass2"},
    )
    assert second.status_code == 400
    assert "Single-user" in second.json()["detail"]


@pytest.mark.asyncio
async def test_get_profile_requires_auth(client):
    response = await client.get("/api/v1/profile")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_profile_crud(client, auth_headers):
    get_resp = await client.get("/api/v1/profile", headers=auth_headers)
    assert get_resp.status_code == 200
    assert "legal_name" in get_resp.json()

    patch_resp = await client.patch(
        "/api/v1/profile",
        headers=auth_headers,
        json={
            "legal_name": "Test User",
            "location_city": "Charlottetown",
            "location_province": "PE",
            "work_authorization": "pgwp",
            "preferred_provinces": ["PE"],
            "preferred_job_categories": ["production", "ai"],
            "salary_min_cad": 55000,
            "salary_max_cad": 90000,
            "languages": {"english": "fluent"},
            "skills": ["Python"],
            "immigration_goals": {"pei_pnp": True, "target_noc_codes": ["21232"]},
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["legal_name"] == "Test User"
    assert data["location_province"] == "PE"
    assert data["preferred_provinces"] == ["PE"]
    assert data["preferred_job_categories"] == ["production", "ai"]
    assert data["salary_min_cad"] == 55000
    assert data["skills"] == ["Python"]


@pytest.mark.asyncio
async def test_auth_me(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "apitest@example.com"
