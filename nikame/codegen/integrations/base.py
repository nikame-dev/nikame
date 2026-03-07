"""Base Integration Interface for NIKAME Matrix Engine.

All integrations must inherit from BaseIntegration and implement the
required lifecycle methods. The MatrixEngine will discover and orchestrate
these classes based on their declarative dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


@dataclass
class OptimizationProfile:
    """Tuning parameters computed centrally by the Matrix Engine.
    
    Passed to every integration to ensure consistent settings across
    cache TTLs, connection pools, and partition counts based on user scale.
    """
    project_scale: str        # e.g., "small", "medium", "large"
    access_pattern: str       # e.g., "read_heavy", "write_heavy", "balanced"
    max_connections: int      # e.g., 25, 100, 500
    cache_ttl_seconds: int    # e.g., 3600 for read_heavy, 300 for write_heavy
    kafka_partitions: int     # e.g., 3, 6, 12
    worker_concurrency: int   # e.g., 2, 8, 32


class BaseIntegration(ABC):
    """The strict contract for a NIKAME Integration.
    
    Integrations are only triggered when ALL required modules/features are present.
    If triggered, the integration MUST generate all 5 components:
      1. Core logic
      2. Lifespan startup hooks
      3. Health check endpoints
      4. Metrics endpoints
      5. GUIDE.md documentation
    """

    # Declarative Dependency Injection
    REQUIRED_MODULES: list[str] = []
    REQUIRED_FEATURES: list[str] = []
    DEPENDS_ON: list[str] = [] # Names of other integrations that must run first

    def __init__(
        self,
        config: NikameConfig,
        blueprint: Blueprint,
        profile: OptimizationProfile,
    ) -> None:
        self.config = config
        self.blueprint = blueprint
        self.profile = profile
        
        # A quick lookup for active modules/features 
        self.active_modules = {m.NAME for m in blueprint.modules}
        self.active_features = set(config.features)

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Evaluate if this integration's conditions are met."""
        if not all(m in active_modules for m in cls.REQUIRED_MODULES):
            return False
        if not all(f in active_features for f in cls.REQUIRED_FEATURES):
            return False
        # Do not load if the lists are empty (base class abstraction)
        if not cls.REQUIRED_MODULES and not cls.REQUIRED_FEATURES:
            return False
        return True

    @abstractmethod
    def generate_core(self) -> list[tuple[str, str]]:
        """Generate the core application logic.
        
        Returns:
            List of (relative_path, file_content) tuples.
            e.g. [("app/core/integrations/rag.py", "...")]
        """
        pass

    @abstractmethod
    def generate_lifespan(self) -> str:
        """Generate the startup/shutdown code block.
        
        Will be injected into `app/main.py`'s @asynccontextmanager lifespan.
        """
        pass

    @abstractmethod
    def generate_health(self) -> dict[str, str]:
        """Generate the health check dict.
        
        Returns:
            A dict segment representing the system health check logic.
            e.g {"qdrant_status": "await qdrant.is_ready()"}
        """
        pass

    @abstractmethod
    def generate_metrics(self) -> str:
        """Generate Prometheus metrics initialization.
        
        Returns:
            Code block creating tracking metrics (e.g. Counter, Histogram).
        """
        pass

    @abstractmethod
    def generate_guide(self) -> str:
        """Generate the documentation for GUIDE.md.
        
        Returns:
            Markdown explaining how to use this integration.
        """
        pass
