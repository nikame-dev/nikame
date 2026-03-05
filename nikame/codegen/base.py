"""Base classes for NIKAME application code generation.

Provides the contract for modular feature generation (Auth, Payments, etc.)
that can be injected into the base application scaffold.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from nikame.config.schema import NikameConfig


@dataclass
class CodegenContext:
    """Context for application code generation.

    Contains all metadata required to render feature templates correctly
    and wire them into the existing application structure.

    Attributes:
        project_name: Sanitized project name.
        active_modules: List of infrastructure module NAMEs (e.g., ['postgres']).
        database_url: Connection string for the primary database.
        cache_url: Connection string for the cache provider.
        api_port: Port the FastAPI application is listening on.
        features: List of selected feature NAMEs (e.g., ['auth', 'payments']).
    """

    project_name: str
    active_modules: list[str]
    database_url: str = ""
    cache_url: str = ""
    api_port: int = 8000
    features: list[str] = field(default_factory=list)


@dataclass
class WiringInfo:
    """Metadata for wiring a feature into the application."""

    imports: list[str] = field(default_factory=list)
    routers: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)


class BaseCodegen(ABC):
    """Abstract base class for all NIKAME codegen features.

    Each feature (e.g., AuthCodegen) implements this interface to provide
    the necessary files, migrations, and routing logic.

    Attributes:
        NAME: Unique identifier for the feature (e.g., "auth").
        DESCRIPTION: Human-readable description of what this feature adds.
        DEPENDENCIES: Other feature NAMEs required by this feature.
        MODULE_DEPENDENCIES: Infrastructure module NAMEs required (e.g., ["postgres"]).
    """

    NAME: str
    DESCRIPTION: str
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = []

    def __init__(self, ctx: CodegenContext, config: NikameConfig | None = None) -> None:
        """Initialize the codegen feature with project context.

        Args:
            ctx: The shared generation context.
            config: The full project configuration (optional for some features).
        """
        self.ctx = ctx
        self.config = config

    @abstractmethod
    def generate(self) -> list[tuple[str, str]]:
        """Generate the application files for this feature.

        Returns:
            List of (relative_path, content) tuples to be written to disk.
        """
        pass

    def wiring(self) -> WiringInfo:
        """Return the wiring info for this feature."""
        return WiringInfo()

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Return K8s manifests for this feature."""
        return []

    def dependencies(self) -> list[str]:
        """Return the list of feature dependencies."""
        return list(self.DEPENDENCIES)

    def module_dependencies(self) -> list[str]:
        """Return the list of infrastructure module dependencies."""
        return list(self.MODULE_DEPENDENCIES)
