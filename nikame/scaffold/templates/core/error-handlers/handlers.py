"""
Global exception handlers.

Registers standardized responses for FastAPI exceptions and
our custom `AppException` hierarchy.
"""
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from {{APP_NAME}}.core.exceptions import AppException
from {{APP_NAME}}.core.response import ErrorDetail, StandardResponse, create_error_response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles all custom internal AppExceptions."""
    error_detail = ErrorDetail(
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    return create_error_response(error_detail, exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
    """Standardizes Pydantic/FastAPI validation errors."""
    details: list[dict[str, Any]] = []
    for error in exc.errors():
        details.append({
            "loc": ".".join(map(str, error.get("loc", []))),
            "msg": error.get("msg"),
            "type": error.get("type"),
        })
        
    error_detail = ErrorDetail(
        code="validation_error",
        message="Request validation failed.",
        details={"errors": details},
    )
    return create_error_response(error_detail, status.HTTP_422_UNPROCESSABLE_ENTITY)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions to prevent leaking tracebacks."""
    # Note: In production you should log this exception using structlog or similar
    error_detail = ErrorDetail(
        code="internal_server_error",
        message="An unexpected server error occurred.",
    )
    return create_error_response(error_detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


def register_error_handlers(app: FastAPI) -> None:
    """Mounts all global exception handlers onto the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
