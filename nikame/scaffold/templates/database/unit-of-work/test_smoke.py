import pytest
from app.database.uow import UnitOfWork

class MockSession:
    def __init__(self):
        self.committed = False
        self.rollbacked = False
        
    async def commit(self):
        self.committed = True
        
    async def rollback(self):
        self.rollbacked = True

@pytest.mark.asyncio
async def test_uow_auto_commits_on_success():
    session = MockSession()
    uow = UnitOfWork(session) # type: ignore
    
    async with uow:
        pass # Action goes here
        
    assert session.committed is True
    assert session.rollbacked is False

@pytest.mark.asyncio
async def test_uow_rollbacks_on_exception():
    session = MockSession()
    uow = UnitOfWork(session) # type: ignore
    
    try:
        async with uow:
            raise ValueError("Something bad happened deep in the repo")
    except ValueError:
        pass
        
    assert session.committed is False
    assert session.rollbacked is True
