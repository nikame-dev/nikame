import base64
from typing import Any, Generic, List, Optional, TypeVar
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class CursorPage(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None
    has_next: bool

class CursorParams(BaseModel):
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)

def get_cursor_params(
    cursor: Optional[str] = Query(None, description="Cursor for the next page"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> CursorParams:
    return CursorParams(cursor=cursor, limit=limit)

def encode_cursor(val: Any) -> str:
    """Encodes a cursor value to a url-safe base64 string."""
    return base64.urlsafe_b64encode(str(val).encode()).decode()

def decode_cursor(cursor: str, type_func: type = int) -> Any:
    """Decodes a base64 cursor back to its original type."""
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        return type_func(decoded)
    except (ValueError, TypeError):
        return None

async def paginate_cursor(
    session: AsyncSession,
    query: Select,
    params: CursorParams,
    cursor_column: Any,
    decode_func: type = int
) -> CursorPage[Any]:
    """
    Executes a cursor-paginated query.
    Requires `cursor_column` to be explicitly provided (e.g., User.id or User.created_at).
    """
    
    # +1 to know if there's a next page
    fetch_limit = params.limit + 1
    
    # We assume ascending order for simplicity here
    paginated_query = query.order_by(cursor_column.asc()).limit(fetch_limit)
    
    if params.cursor:
        decoded_val = decode_cursor(params.cursor, decode_func)
        if decoded_val is not None:
            # Only fetch items greater than the cursor
            paginated_query = paginated_query.where(cursor_column > decoded_val)
            
    result = await session.execute(paginated_query)
    items = list(result.scalars().all())

    has_next = len(items) > params.limit
    if has_next:
        items = items[:-1] # Remove the +1 we fetched
        
    next_cursor = None
    if items:
        # Extract the value of the cursor column from the very last item
        # SQLA models can be accessed via getattr
        last_item_val = getattr(items[-1], cursor_column.name, None)
        if last_item_val is not None:
            next_cursor = encode_cursor(last_item_val)

    return CursorPage(
        items=items,
        next_cursor=next_cursor,
        has_next=has_next
    )
