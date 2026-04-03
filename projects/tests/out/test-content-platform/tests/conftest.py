import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as aioredis

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client for the FastAPI application."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Create a test database session.

    Override the app's database dependency with a test database.
    Set TEST_DATABASE_URL in your environment or .env.test file.
    """
    test_db_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
    )
    engine = create_async_engine(test_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def redis_client():
    """Create a test Redis client."""
    test_redis_url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")
    client = aioredis.from_url(test_redis_url)
    yield client
    await client.aclose()
