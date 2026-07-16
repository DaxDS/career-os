import pytest


@pytest.mark.asyncio
async def test_foundation_status_endpoint(client):
    response = await client.get("/api/v1/foundation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["audit_logging"] == "ready"
    assert "file_storage" in data
    assert "prompt_registry" in data
    assert data["prompt_registry"]["registered_count"] >= 8
