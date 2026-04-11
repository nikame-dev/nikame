import abc
from typing import Callable, Coroutine, Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.database.session import get_db

# Assuming BaseRepository is available (from fastcheat add database/repository)
# from app.database.repository import BaseRepository

class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    @abc.abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError

class UnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy specific implementation of the Unit of Work.
    Injects a single DB session into multiple repositories.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        # Initialize repositories sharing the same session here
        # self.users = UserRepository(self.session)
        # self.items = ItemRepository(self.session)

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


async def get_uow(session: AsyncSession = Depends(get_db)) -> UnitOfWork:
    """Dependency that yields a Unit of Work."""
    return UnitOfWork(session=session)
