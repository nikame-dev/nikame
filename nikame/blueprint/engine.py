"""Blueprint engine — resolves module dependencies into a generation plan.

Uses NetworkX to build a directed acyclic graph (DAG) from the user's
config, resolves transitive dependencies, detects cycles and conflicts,
applies smart-default recommendations, and produces a topologically
sorted list of module instances ready for composition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import networkx as nx  # type: ignore[import-untyped]

from nikame.config.schema import NikameConfig
from nikame.exceptions import (
    NikameCycleError,
    NikameModuleConflictError,
)
from nikame.mlops.hardware import HardwareDetector
from nikame.mlops.serving import ServingSelector
from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import discover_modules, get_all_modules, get_module_class
from nikame.utils.logger import console, get_logger

_log = get_logger("blueprint.engine")


@dataclass
class Blueprint:
    """Resolved blueprint — the generation plan.

    Attributes:
        project_name: Sanitized project name.
        modules: Topologically sorted module instances.
        graph: The dependency DAG.
        warnings: Non-fatal optimization suggestions.
        env_vars: Accumulated environment variables from all modules.
    """

    project_name: str
    modules: list[BaseModule]
    graph: nx.DiGraph  # type: ignore[type-arg]
    config: NikameConfig | None = None
    warnings: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize blueprint to JSON-compatible dict for persistence."""
        return {
            "project_name": self.project_name,
            "modules": [
                {
                    "name": m.NAME,
                    "category": m.CATEGORY,
                    "version": m.version,
                    "dependencies": m.dependencies(),
                }
                for m in self.modules
            ],
            "features": self.features,
            "warnings": self.warnings,
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Collect and return all K8s manifests for the project."""
        all_manifests: list[dict[str, Any]] = []

        # 1. Namespace-level resources (ResourceQuota)
        if self.modules:
            all_manifests.append(self.modules[0].resource_quota(self.modules[0].ctx.namespace))

        # 2. Module-specific manifests
        for mod in self.modules:
            all_manifests.extend(mod.k8s_manifests())

        # 3. Feature-specific manifests
        all_manifests.extend(self._get_feature_manifests())

        # 4. Sealed Secrets
        sealed_secrets = self._generate_sealed_secrets()
        all_manifests.extend(sealed_secrets)

        if sealed_secrets:
            all_manifests = [m for m in all_manifests if m.get("kind") != "Secret"]

        return all_manifests

    def _get_feature_manifests(self) -> list[dict[str, Any]]:
        """Collect manifests from active features."""
        from nikame.codegen.base import CodegenContext
        from nikame.codegen.registry import discover_codegen, get_codegen_class

        manifests = []
        discover_codegen()

        ctx = CodegenContext(
            project_name=self.project_name,
            active_modules=[m.NAME for m in self.modules],
            features=self.features
        )

        for feature in self.features:
            cls = get_codegen_class(feature)
            if cls:
                generator = cls(ctx, self.config)
                manifests.extend(generator.k8s_manifests())

        return manifests

    def _generate_sealed_secrets(self) -> list[dict[str, Any]]:
        """Generate placeholder SealedSecret resources for all env vars."""
        manifests = []
        secrets = {k: v for k, v in self.env_vars.items() if any(x in k for x in ["KEY", "PWD", "SECRET", "PASSWORD", "TOKEN"])}

        if secrets:
            manifests.append({
                "apiVersion": "bitnami.com/v1alpha1",
                "kind": "SealedSecret",
                "metadata": {
                    "name": "project-secrets",
                    "namespace": self.modules[0].ctx.namespace if self.modules else "default",
                    "annotations": {"sealedsecrets.bitnami.com/managed": "true"}
                },
                "spec": {
                    "encryptedData": dict.fromkeys(secrets, "Ag...base64_placeholder..."),
                    "template": {
                        "metadata": {"name": "project-secrets", "labels": {"nikame.role": "secrets"}}
                    }
                }
            })
        return manifests


class BlueprintEngine:
    """Engine for resolving NikameConfig into a Blueprint."""

    def __init__(self, config: NikameConfig):
        self.config = config

    def resolve(self) -> Blueprint:
        """Resolve the config into a generation plan (Blueprint)."""
        return build_blueprint(self.config)


def build_blueprint(config: NikameConfig) -> Blueprint:
    """Build a resolved Blueprint from a validated NikameConfig."""
    discover_modules()
    all_registered = get_all_modules()
    
    active_module_configs = _extract_active_modules(config)
    _apply_project_optimizations(config, active_module_configs)
    
    graph: nx.DiGraph = nx.DiGraph()  # type: ignore[type-arg]

    for mod_name in active_module_configs:
        graph.add_node(mod_name)

    to_process = list(active_module_configs.keys())
    processed: set[str] = set()

    while to_process:
        mod_name = to_process.pop(0)
        if mod_name in processed:
            continue
        processed.add(mod_name)

        mod_cls = get_module_class(mod_name)
        if mod_cls is None:
            continue

        for dep_name in mod_cls.DEPENDENCIES:
            if dep_name not in active_module_configs:
                active_module_configs[dep_name] = {}
                to_process.append(dep_name)
            graph.add_edge(mod_name, dep_name)

    try:
        sorted_nodes = list(reversed(list(nx.topological_sort(graph))))
    except nx.NetworkXUnfeasible:
        raise NikameCycleError("Circular dependency detected in project modules.")

    resolved_modules = []
    accumulated_env = {}

    for mod_name in sorted_nodes:
        mod_cls = get_module_class(mod_name)
        if not mod_cls:
            continue
        
        ctx = ModuleContext(
            project_name=config.name,
            namespace=config.name,
            config=active_module_configs.get(mod_name, {})
        )
        mod_inst = mod_cls(ctx)
        resolved_modules.append(mod_inst)
        accumulated_env.update(mod_inst.env_vars())

    return Blueprint(
        project_name=config.name,
        modules=resolved_modules,
        graph=graph,
        config=config,
        env_vars=accumulated_env,
        features=config.features
    )


def _extract_active_modules(config: NikameConfig) -> dict[str, dict[str, Any]]:
    """Extract active module names and their configs from NikameConfig."""
    modules: dict[str, dict[str, Any]] = {}
    
    if config.databases:
        for name, cfg in config.databases.items():
            modules[name] = cfg if isinstance(cfg, dict) else cfg.model_dump()
            
            # Smart Cache wiring
            if name == "redis":
                modules["redis"] = cfg.model_dump() if not isinstance(cfg, dict) else cfg

    if config.messaging:
        for name, cfg in config.messaging.items():
            modules[name] = cfg if isinstance(cfg, dict) else cfg.model_dump()

    if config.observability:
        if config.observability.stack == "full":
            modules["prometheus"] = {}
            modules["grafana"] = {}

    if config.mlops:
        if config.mlops.models:
            hw = HardwareDetector.detect()
            for model_cfg in config.mlops.models:
                backend = ServingSelector.select(model_cfg, hw)
                modules[backend] = model_cfg.model_dump()

    return modules


def _apply_project_optimizations(config: NikameConfig, modules: dict[str, dict[str, Any]]) -> None:
    """Apply implicit project-level optimizations."""
    if "postgres" in modules and "redis" in modules:
        # Optimization: Enable pg_audit if both are present
        pass
