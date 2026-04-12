from typing import Any


class NikameError(Exception):
    """Base exception for all NIKAME errors."""
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.details = details


class ConfigValidationError(NikameError):
    """Raised when the nikame.yaml configuration is invalid."""
    pass


class ManifestError(NikameError):
    """Raised when the project manifest (.nikame/context.yaml) is corrupted or invalid."""
    pass


class RegistryError(NikameError):
    """Raised when a pattern registry or pattern manifest cannot be loaded."""
    pass


class DependencyConflictError(RegistryError):
    """Raised when pattern dependencies or conflicts cannot be resolved."""
    pass


class ResourceAllocationError(NikameError):
    """Raised when system resources (ports, DBs) cannot be allocated."""
    pass


class VerificationError(NikameError):
    """Raised when a project fails static verification."""
    pass


class RollbackError(NikameError):
    """Raised when a rollback operation fails."""
    pass


class CopilotError(NikameError):
    """Base exception for AI-related errors."""
    pass
