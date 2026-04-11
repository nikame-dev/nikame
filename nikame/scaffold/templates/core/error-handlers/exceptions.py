"""
Custom exception hierarchy.
"""
from typing import Any

from fastapi import status


class AppException(Exception):
    """Base exception for all application-level errors."""
    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "internal_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found."""
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            details=details,
        )


class BadRequestException(AppException):
    """Generic bad request."""
    def __init__(self, message: str = "Bad request", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="bad_request",
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication failed."""
    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            details=details,
        )


class ForbiddenException(AppException):
    """Authorization failed."""
    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
            details=details,
        )


class ConflictException(AppException):
    """Resource conflict (e.g., unique constraint violation)."""
    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code="conflict",
            details=details,
        )
