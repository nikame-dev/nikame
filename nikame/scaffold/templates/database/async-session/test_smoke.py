import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db, engine

@pytest.mark.asyncio
async def test_get_db_yields_session():
    # Due to 'sqlite+aiosqlite' testing limits or postgres limits,
    # we just assert the generator returns an object that looks like a session.
    # We do NOT run a query to prevent requiring a DB in CI smoke tests.
    generator_instance = get_db()
    session = await generator_instance.__anext__()
    
    assert isinstance(session, AsyncSession)
    
    # Normally handled by `async with` but here we just manually close to prevent unclosed connection warnings
    await session.close()
