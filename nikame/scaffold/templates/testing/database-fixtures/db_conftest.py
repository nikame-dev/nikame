import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database.session import Base, get_db

# Use a separate test database!
TEST_DB_URL = "{{TEST_DATABASE_URL}}" or "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    
    # Create tables once per test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an atomic database session.
    Every test runs inside a nested transaction (savepoint) 
    and is automatically rolled back at the end.
    This is 100x faster than recreating the database.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    
    session_factory = async_sessionmaker(connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture
async def override_get_db(app, db_session):
    """
    Injects the test session into the FastAPI application.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()
