"""The Matrix Engine: Central Intelligence Layer.

Detects active modules, builds a dependency DAG of integrations, computes
the OptimizationProfile, and generates the consolidated integration layer.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections import defaultdict, deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nikame.codegen.integrations.base import BaseIntegration, OptimizationProfile
from nikame.utils.logger import get_logger

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig
    from nikame.utils.file_writer import FileWriter

_log = get_logger("matrix_engine")


class MatrixEngine:
    """Orchestrates all cross-module capabilities dynamically."""

    def __init__(self, config: NikameConfig, blueprint: Blueprint, writer: FileWriter) -> None:
        self.config = config
        self.blueprint = blueprint
        self.writer = writer
        
        self.active_modules = {m.NAME for m in blueprint.modules}
        self.active_features = set(config.features)
        
        # Integration class registry: Name -> Class
        self._registry: dict[str, type[BaseIntegration]] = {}
        
        self._discover_integrations()

    def _discover_integrations(self) -> None:
        """Auto-discover all BaseIntegration subclasses in the directory."""
        package_path = Path(__file__).parent.resolve()
        package_name = "nikame.codegen.integrations"

        for _, modname, _ in pkgutil.walk_packages([str(package_path)], prefix=f"{package_name}."):
            if modname.split(".")[-1] in ("base", "matrix"):
                continue

            try:
                module = importlib.import_module(modname)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseIntegration)
                        and attr is not BaseIntegration
                    ):
                        self._registry[attr.__name__] = attr
            except Exception as e:
                _log.warning(f"Failed to import integration module {modname}: {e}")

    def _compute_profile(self) -> OptimizationProfile:
        """Compute system variables based on project metadata."""
        scale = getattr(self.config, "scale", "medium")
        pattern = getattr(self.config, "access_pattern", "balanced")
        
        # Scale sizing
        if scale == "small":
            max_conn, workers, partitions = 10, 2, 3
        elif scale == "large":
            max_conn, workers, partitions = 100, 16, 12
        else: # medium
            max_conn, workers, partitions = 25, 4, 6
            
        # Pattern tuning
        if pattern == "read_heavy":
            cache_ttl = 3600 * 24 # 24hrs
        elif pattern == "write_heavy":
            cache_ttl = 300 # 5min
        else: # balanced
            cache_ttl = 3600 # 1hr

        return OptimizationProfile(
            project_scale=scale,
            access_pattern=pattern,
            max_connections=max_conn,
            cache_ttl_seconds=cache_ttl,
            kafka_partitions=partitions,
            worker_concurrency=workers
        )

    def _topological_sort(self, triggered: list[BaseIntegration]) -> list[BaseIntegration]:
        """Sort implementations dynamically via their DEPENDS_ON property."""
        name_to_inst = {inst.__class__.__name__: inst for inst in triggered}
        
        # Build graph
        graph: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {inst.__class__.__name__: 0 for inst in triggered}
        
        for inst in triggered:
            cls_name = inst.__class__.__name__
            for dep in inst.DEPENDS_ON:
                if dep in name_to_inst:
                    graph[dep].append(cls_name)
                    in_degree[cls_name] += 1
                    
        # Kahn's algorithm
        queue = deque([k for k, v in in_degree.items() if v == 0])
        sorted_names = []
        
        while queue:
            node = queue.popleft()
            sorted_names.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(sorted_names) != len(triggered):
            _log.error("Matrix engine detected a circular dependency in integrations!")
            # Fallback to an arbitrary order if circle is found (should be avoided)
            return triggered
            
        return [name_to_inst[name] for name in sorted_names]

    def execute(self) -> None:
        """Discover, score, sort, and dispatch integrations."""
        profile = self._compute_profile()
        _log.info(f"Matrix computed profile: Scale '{profile.project_scale}', Access '{profile.access_pattern}'")

        # 1. First, instantiate all triggered integrations
        triggered_instances = []
        for name, cls in self._registry.items():
            if cls.should_trigger(self.active_modules, self.active_features):
                # Instantiate with computed profile
                instance = cls(self.config, self.blueprint, profile)
                triggered_instances.append(instance)
                _log.debug(f"Matrix flagged integration: {name}")

        if not triggered_instances:
            _log.debug("No matrix integrations triggered.")
            return

        # 2. Sort the INSTANCES based on their class DEPENDS_ON rules
        sorted_instances = self._topological_sort(triggered_instances)

        _log.info(f"Matrix dispatching {len(sorted_instances)} configured integrations.")
        
        # Aggregated outputs to be injected into main systems
        lifespans = []
        health_checks = {}
        metrics_blocks = []
        guides = []
        
        for integration in sorted_instances:
            # 1. Write core output files independent of main.py
            for path, content in integration.generate_core():
                _log.info(f"Matrix writing integration file: {path}")
                self.writer.write_file(path, content)
                
            # 2. Collect aggregation blocks
            lifespans.append(integration.generate_lifespan())
            health_checks.update(integration.generate_health())
            metrics_blocks.append(integration.generate_metrics())
            guides.append(integration.generate_guide())

        # 3. Inject the collected components into main templates
        self._inject_into_app(lifespans, health_checks, metrics_blocks)
        
        # 4. Integrate docs directly
        if guides:
            # We assume a mechanism to write the guide back to documentation layer
            # which could be handled natively or passing back to guide generator.
            combined_guide = "\n\n".join(guides)
            self.writer.write_file("docs/integrations.md", combined_guide)
            
    def _inject_into_app(
        self,
        lifespans: list[str],
        health_checks: dict[str, str],
        metrics: list[str]
    ) -> None:
        """Mock injection into main system. In reality, you'd pass these
        strings into Jinja schemas and render main.py with them.
        """
        # For Phase 1 we just store them to log / show testing correctness.
        pass
