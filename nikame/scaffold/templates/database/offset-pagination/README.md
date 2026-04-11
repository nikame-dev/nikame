# Offset Pagination

A classic `OFFSET/LIMIT` pagination strategy returning rigorous metadata (`total_pages`, `has_next`).

## Usage

Inject `get_pagination_params` into your endpoint, then use the `paginate` helper.

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.offset_pagination import Page, PaginationParams, get_pagination_params, paginate

router = APIRouter()

@router.get("/users", response_model=Page[UserSchema])
async def list_users(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    # Formulate your query without limit/offset
    query = select(User).where(User.is_active == True)
    
    return await paginate(db, query, params)
```

## Gotchas

* Offset pagination degrades in performance linearly with size. Fetching `page=100_000` is deeply expensive for SQL databases. Use Cursor Pagination for massive datasets.
* The module executes a secondary `.count()` query natively in the background to fulfill the `meta` calculations. So every `paginate()` executes 2 actual SQL queries.
