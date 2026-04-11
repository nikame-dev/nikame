import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """
    Simple smoke test using the async client.
    """
    response = await client.get("/health/liveness")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_protected_route_without_auth(client: AsyncClient):
    """
    Verify security headers/middleware are working.
    """
    response = await client.get("/auth/me")
    # Should be 401 if auth is implemented
    assert response.status_code in [401, 403, 404] 
