"""NIKAME custom exceptions.

All user-facing errors inherit from NikameError. Validation errors
(config/schema) use NikameValidationError; file-generation failures
use NikameGenerationError.
"""


class NikameError(Exception):
    """Base exception for all NIKAME errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class NikameValidationError(NikameError):
    """Raised when nikame.yaml or module config fails validation.

    Caught at parse time, shown to user with rich formatting.
    """


class NikameGenerationError(NikameError):
    """Raised when file generation fails.

    Covers template rendering errors, file I/O errors, and
    composer merge failures.
    """


class NikameModuleConflictError(NikameValidationError):
    """Raised when two modules in the blueprint conflict."""


class NikameDependencyError(NikameValidationError):
    """Raised when a module's dependency is missing from the blueprint."""


class NikameCycleError(NikameValidationError):
    """Raised when the module dependency graph has a cycle."""
