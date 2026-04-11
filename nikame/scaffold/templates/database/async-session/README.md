# Async SQLAlchemy Session

Provides the core engine setup and the `get_db` generator that supplies async sessions to your request context.

## Usage

Use it in your router injection targets:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database.session import get_db

router = APIRouter()

@router.get("/now")
async def get_time(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT NOW()"))
    return {"db_time": result.scalar()}
```

## Gotchas

* `expire_on_commit=False` is set by default. This is critical in `sqlalchemy.ext.asyncio` because lazy-loading attributes outside the initial await will trigger a nasty `MissingGreenlet` error. You must explicitly eagerly load (`joinedload` or `selectinload`) all data you need.
* Requires the `asyncpg` DB driver.
