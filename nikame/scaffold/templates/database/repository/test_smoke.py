import pytest
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repository import BaseRepository

class Base(DeclarativeBase):
    pass

class DummyModel(Base):
    __tablename__ = "dummy"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

class DummyCreate(BaseModel):
    name: str

class DummyUpdate(BaseModel):
    name: str | None = None

class DummyRepo(BaseRepository[DummyModel, DummyCreate, DummyUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(DummyModel, session)

# Fake SQLAlchemy session mock object because we don't have a real DB in this test execution
class MockSession:
    def __init__(self):
        self.added = []
    def add(self, item):
        self.added.append(item)

@pytest.mark.asyncio
async def test_repo_create_with_pydantic():
    # Pass a dummy mock session in to avoid connecting to postgres during testing
    session = MockSession()
    repo = DummyRepo(session)  # type: ignore
    
    in_schema = DummyCreate(name="Testing")
    res = await repo.create(in_schema)
    
    assert res.name == "Testing"
    assert res in session.added

@pytest.mark.asyncio
async def test_repo_create_with_dict():
    session = MockSession()
    repo = DummyRepo(session)  # type: ignore
    
    res = await repo.create({"name": "TestingDict"})
    
    assert res.name == "TestingDict"
    assert res in session.added
