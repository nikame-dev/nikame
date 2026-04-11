"""
Request-scoped async SQLAlchemy database session.

Creates exactly one DB session per request, yielding it to route handlers.
Ensures cleanly closing the transaction (rollback on exception) and
then releasing the connection back to the pool.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Note: In a real app, engine and session_factory are defined in database/session.py
# and initialized during the app lifespan.
engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency providing an SQLAlchemy AsyncSession scoped to the request.
    
    If no exception is raised in the route handler, the transaction is implicitly
    committed (or you can manually commit it). If an exception is raised, it is
    caught and rolled back here before propagating. Finally, the session is closed.
    """
    session = AsyncSessionLocal()
    try:
        yield session
        # Auto-commit can be enabled here if that's your preferred architectural style:
        # await session.commit()
    except Exception:
        # Rollback on any unhandled exception thrown in the request
        await session.rollback()
        raise
    finally:
        # Ensure connection returned to the pool
        await session.close()
