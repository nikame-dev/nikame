import math
from typing import Any, Generic, List, TypeVar
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class PageMeta(BaseModel):
    page: int
    size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool

class Page(BaseModel, Generic[T]):
    items: List[T]
    meta: PageMeta

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)

async def paginate(
    session: AsyncSession,
    query: Select,
    params: PaginationParams
) -> Page[Any]:
    """
    Executes an offset-based paginated query against SQLAlchemy.
    Automatically executes a second query to COUNT the total items.
    """
    
    # 1. Count query
    # Extracts the underlying FROM clause from the query and builds a count statement cleanly
    count_query = query.with_only_columns(func.count()).order_by(None)
    count_res = await session.execute(count_query)
    total_items = count_res.scalar() or 0
    
    # 2. Main data query
    offset = (params.page - 1) * params.size
    paginated_query = query.offset(offset).limit(params.size)
    
    result = await session.execute(paginated_query)
    items = list(result.scalars().all())
    
    # 3. Calculate Meta
    total_pages = math.ceil(total_items / params.size) if total_items > 0 else 0
    
    meta = PageMeta(
        page=params.page,
        size=params.size,
        total_items=total_items,
        total_pages=total_pages,
        has_previous=params.page > 1,
        has_next=params.page < total_pages
    )
    
    return Page(items=items, meta=meta)
