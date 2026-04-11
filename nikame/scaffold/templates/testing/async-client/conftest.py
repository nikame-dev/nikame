import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from main import app # Adjust import based on project structure

@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest-asyncio's event_loop fixture to be session-scoped."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Standard async client fixture for testing.
    Automatically handles app lifespan (startup/shutdown).
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_auth(monkeypatch):
    """
    Helper to bypass authentication dependencies during tests.
    """
    # Example: Override the get_current_user dependency
    # from app.auth.jwt import get_current_user
    # monkeypatch.setattr("app.auth.jwt.get_current_user", lambda: {"id": 1, "role": "admin"})
    pass
