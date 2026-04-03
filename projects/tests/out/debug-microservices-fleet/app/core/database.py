import os
"""
SQLAlchemy async session management with pooling, health checks, and query helpers.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select
from config import settings
from typing import TypeVar, Type, Optional, List, Any

# Primary engine for Writes
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "25")),
    max_overflow=10,
)

# Replica engine for Reads (defaults to primary if no replica is configured)
read_engine = create_async_engine(
    settings.DATABASE_READ_URL.replace("postgres://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "25")),
    max_overflow=10,
)

# Read/Write Session (Primary)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Read-Only Session (Replica)
AsyncReadSessionLocal = async_sessionmaker(
    bind=read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """Dependency for Read/Write operations."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_read_db():
    """Dependency for Read-Only operations (optimized for replicas)."""
    async with AsyncReadSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

T = TypeVar("T")

class BaseRepository:
    """Generic repository for common queries."""
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[T]:
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: dict) -> T:
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
