# Cursor Pagination

A high-performance pagination strategy suitable for infinite scrolling and massively large database tables. Unlike `OFFSET/LIMIT` (which degrades O(N) over deep pages), cursor pagination uses explicit index lookups to fetch the "next X items after Y".

## Usage

Inject `get_cursor_params` into your endpoint, then use the `paginate_cursor` helper.

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.cursor_pagination import CursorPage, CursorParams, get_cursor_params, paginate_cursor

router = APIRouter()

@router.get("/users", response_model=CursorPage[UserSchema])
async def list_users(
    params: CursorParams = Depends(get_cursor_params),
    db: AsyncSession = Depends(get_db)
):
    query = select(User)
    
    # We must explicitly define what column we are paginating over
    return await paginate_cursor(db, query, params, cursor_column=User.id)
```

## Gotchas

* Cursors only natively work correctly if the `cursor_column` is strictly unique and sequentially comparable (like sequential Integers, UUIDv7, or highly precise timestamps).
* You cannot easily jump to "page 100" with cursor pagination. You can only fetch the "next block".
