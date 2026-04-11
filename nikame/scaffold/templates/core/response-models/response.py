"""
Standardised API response envelope.

Wraps all responses in a consistent JSON structure:
{
    "data": ...,
    "meta": ...,
    "error": ...
}
"""
from typing import Any, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error information."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional context or validation errors")

    model_config = ConfigDict(extra="ignore")


class PaginationMeta(BaseModel):
    """Standard pagination metadata."""
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
    has_next: bool
    has_previous: bool


class StandardResponse(BaseModel, Generic[T]):
    """
    Standard API envelope for all responses.
    
    Fields:
        data: The actual payload (if successful).
        meta: Auxiliary data like pagination or request rates.
        error: Error details (if failed).
    """
    data: T | None = None
    meta: PaginationMeta | dict[str, Any] | None = None
    error: ErrorDetail | None = None

    model_config = ConfigDict(extra="ignore")


def create_success_response(
    data: Any,
    meta: Any = None,
    status_code: int = 200,
) -> JSONResponse:
    """Helper to return a standardized success JSONResponse."""
    content = StandardResponse(data=data, meta=meta).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=content)


def create_error_response(
    error: ErrorDetail,
    status_code: int = 400,
) -> JSONResponse:
    """Helper to return a standardized error JSONResponse."""
    content = StandardResponse(error=error).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=content)
