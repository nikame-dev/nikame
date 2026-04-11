from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import Depends

# Ideally, DATABASE_URL comes from pydantic-settings
# e.g. "postgresql+asyncpg://user:pass@localhost:5432/db"
DATABASE_URL = "{{DATABASE_URL}}"

# Global engine configured with reasonable production defaults
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for debugging queries
    future=True,
    pool_pre_ping=True, # Tests the connection before returning from pool
    pool_size=20,       # Maximum connections to keep open
    max_overflow=10,    # How many extra to open when pool_size is exhausted
)

# Shared factory to produce new sessions
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False, # Important for async, prevents detached instance errors
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session per request.
    The session is cleanly closed on exit, even if exceptions occur.
    """
    async with async_session_factory() as session:
        yield session
