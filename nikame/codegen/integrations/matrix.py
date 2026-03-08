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
        """Auto-discover all BaseIntegration and BaseCodegen subclasses."""
        # 1. Discover BaseIntegration subclasses in the integrations package
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
        
        # 2. Add BaseCodegen subclasses from COMPONENT_REGISTRY
        from nikame.codegen.registry import COMPONENT_REGISTRY
        for key, info in COMPONENT_REGISTRY.items():
            cls = info.get("class")
            if cls:
                self._registry[cls.__name__] = cls

    def _compute_profile(self) -> OptimizationProfile:
        """Compute system variables based on project metadata."""
        scale = self.config.project.scale
        pattern = self.config.project.access_pattern
        tp = self.config.project.type
        
        # Scale sizing
        if scale == "small":
            max_conn, workers, partitions = 10, 2, 3
        elif scale == "large":
            max_conn, workers, partitions = 100, 16, 12
        else: # medium
            max_conn, workers, partitions = 25, 4, 6
            
        # Project Type specific tuning
        if tp == "rag_app":
            # RAG apps are read-heavy on vectors, write-heavy on logs
            max_conn += 20 
        elif tp == "data_pipeline":
            # Pipelines need more partitions
            partitions *= 2
            workers *= 2

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

    def _topological_sort(self, triggered: list[Any]) -> list[Any]:
        """Sort implementations dynamically via their dependencies."""
        name_to_inst = {inst.__class__.__name__: inst for inst in triggered}
        
        # Also map by string NAME for BaseCodegen dependencies
        str_name_to_cls_name = {}
        for inst in triggered:
            if hasattr(inst, "NAME"):
                str_name_to_cls_name[inst.NAME] = inst.__class__.__name__
        
        # Build graph
        graph: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {inst.__class__.__name__: 0 for inst in triggered}
        
        for inst in triggered:
            cls_name = inst.__class__.__name__
            
            deps = getattr(inst, "DEPENDS_ON", [])
            str_deps = getattr(inst, "DEPENDENCIES", [])
            
            all_deps = list(deps)
            for d in str_deps:
                if d in str_name_to_cls_name:
                    all_deps.append(str_name_to_cls_name[d])

            for dep_cls in all_deps:
                if dep_cls in name_to_inst:
                    graph[dep_cls].append(cls_name)
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
                # Instantiate with computed profile or appropriate signatures
                if issubclass(cls, BaseIntegration):
                    instance = cls(self.config, self.blueprint, profile)
                else:
                    # BaseCodegen signature: (ctx, config)
                    from nikame.codegen.base import CodegenContext
                    ctx = CodegenContext(
                        project_name=self.config.name,
                        active_modules=list(self.active_modules),
                        features=list(self.active_features)
                    )
                    instance = cls(ctx, self.config)
                
                triggered_instances.append(instance)
                _log.debug(f"Matrix flagged: {name}")

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
            # 1. Write core output files
            # Check if it's a BaseIntegration or BaseCodegen (they have different method names)
            if isinstance(integration, BaseIntegration):
                for path, content in integration.generate_core():
                    _log.info(f"Matrix writing integration file: {path}")
                    self.writer.write_file(path, content)
                
                # 2. Collect aggregation blocks
                lifespans.append(integration.generate_lifespan())
                health_checks.update(integration.generate_health())
                metrics_blocks.append(integration.generate_metrics())
                guides.append(integration.generate_guide())
            else:
                # BaseCodegen style
                for path, content in integration.generate():
                    _log.info(f"Matrix writing component file: {path}")
                    self.writer.write_file(path, content)
                
                # For components, guide metadata is handled slightly differently
                # but we can still extract it
                guides.append(f"### {integration.NAME}\n{integration.DESCRIPTION}\n")

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
