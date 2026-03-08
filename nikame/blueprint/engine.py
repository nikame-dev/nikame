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
        # We use a dummy instance to access the helper
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

        # 5. Security Filtering: No raw Secrets if using SealedSecrets
        # (Assuming we have access to config or security setting via context if needed)
        # For Item 1 requirement, we always filter if SealedSecrets are generated
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
        # In a real scenario, this would call 'kubeseal'
        # Here we emit the structure to satisfy the architectural requirement
        manifests = []
        # Filter for secrets (simple heuristic: contains KEY, PWD, SECRET, or PASSWORD)
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


def _extract_active_modules(config: NikameConfig) -> dict[str, dict[str, Any]]:
    """Extract active module names and their configs from NikameConfig.

    Walks through the config sections and maps them to module NAMEs.

    Args:
        config: Validated NikameConfig.

    Returns:
        Dict of module_name → config_dict.
    """
    modules: dict[str, dict[str, Any]] = {}

    # API framework
    if config.api:
        modules["fastapi"] = config.api.model_dump()

    # Databases
    if config.databases:
        if config.databases.postgres is not None:
            modules["postgres"] = config.databases.postgres.model_dump()
        if config.databases.redis is not None:
            modules["redis"] = config.databases.redis.model_dump()
        if config.databases.mongodb is not None:
            modules["mongodb"] = config.databases.mongodb
        if config.databases.clickhouse is not None:
            modules["clickhouse"] = config.databases.clickhouse
        if config.databases.qdrant is not None:
            modules["qdrant"] = config.databases.qdrant
        if config.databases.timescaledb is not None:
            modules["timescaledb"] = config.databases.timescaledb
        if config.databases.elasticsearch is not None:
            modules["elasticsearch"] = config.databases.elasticsearch
        if config.databases.neo4j is not None:
            modules["neo4j"] = config.databases.neo4j

    # Messaging
    if config.messaging:
        if config.messaging.redpanda is not None:
            modules["redpanda"] = config.messaging.redpanda.model_dump()
        if config.messaging.kafka is not None:
            modules["kafka"] = config.messaging.kafka
        if config.messaging.rabbitmq is not None:
            modules["rabbitmq"] = config.messaging.rabbitmq
        if config.messaging.nats is not None:
            modules["nats"] = config.messaging.nats
        if config.messaging.temporal is not None:
            modules["temporal"] = config.messaging.temporal

    # Cache
    if config.cache:
        provider = config.cache.provider
        if provider == "dragonfly":
            modules["dragonfly"] = config.cache.dragonfly.model_dump()

    # Storage
    if config.storage:
        modules[config.storage.provider] = config.storage.model_dump()

    # Auth
    if config.auth:
        modules[config.auth.provider] = config.auth.model_dump()

    # Gateway
    if config.gateway:
        modules[config.gateway.provider] = config.gateway.model_dump()

    # Observability
    if config.observability and config.observability.stack != "none":
        modules["prometheus"] = config.observability.model_dump()
        modules["grafana"] = config.observability.model_dump()
        if config.observability.loki:
            modules["loki"] = {}
        if config.observability.tempo:
            modules["tempo"] = {}
        if config.observability.otel_collector:
            modules["otel_collector"] = {}
        if config.observability.uptime_kuma:
            modules["uptime_kuma"] = {}

    # CI/CD
    if config.ci_cd:
        if config.ci_cd.gitea:
            modules["gitea"] = {}
        if config.ci_cd.woodpecker:
            modules["woodpecker"] = {}
        if config.ci_cd.argocd:
            modules["argocd"] = {}
        if config.ci_cd.github_actions:
            modules["github_actions"] = {}

    # Tools
    if config.ngrok is not None:
        modules["ngrok"] = config.ngrok
    if config.unleash is not None:
        modules["unleash"] = config.unleash

    # MLOps
    if config.mlops:
        # 1. Models
        if config.mlops.models:
            hw = HardwareDetector.detect()
            for model_cfg in config.mlops.models:
                backend = ServingSelector.select(model_cfg, hw)
                modules[backend] = model_cfg.model_dump()

        # 2. Serving
        from nikame.config.schema import ServingConfig, TrackingConfig, OrchestrationConfig
        
        if isinstance(config.mlops.serving, ServingConfig):
            if config.mlops.serving.provider != "auto":
                modules[config.mlops.serving.provider] = config.mlops.serving.model_dump()
        else:
            for mod_name in config.mlops.serving:
                modules[mod_name] = {}

        # 3. Tracking
        if isinstance(config.mlops.tracking, TrackingConfig):
            modules[config.mlops.tracking.provider] = config.mlops.tracking.model_dump()
        else:
            for mod_name in config.mlops.tracking:
                modules[mod_name] = {}

        # 4. Orchestration
        if isinstance(config.mlops.orchestration, OrchestrationConfig):
            modules[config.mlops.orchestration.provider] = config.mlops.orchestration.model_dump()
        else:
            for mod_name in config.mlops.orchestration:
                modules[mod_name] = {}

        # 5. Lists (Legacy/Simple)
        for ml_list in [
            config.mlops.feature_store,
            config.mlops.monitoring,
            config.mlops.vector_dbs,
            config.mlops.caching,
            config.mlops.agents,
        ]:
            for mod_name in ml_list:
                modules[mod_name] = {}

    # MLOps models (legacy fallback check)
    elif config.mlops and config.mlops.models:

        # Add the unified gateway
        modules["ml-gateway"] = {"model_services": model_services}
        modules["model-downloader"] = {}

    return modules


def _apply_project_optimizations(config: NikameConfig, modules: dict[str, dict[str, Any]]) -> None:
    """Apply architectural optimizations based on project metadata."""
    if not config.project:
        return

    scale = config.project.scale
    access = config.project.access_pattern
    
    # 1. Scale-driven optimizations
    if scale == "medium":
        if "postgres" in modules:
            modules["postgres"]["replicas"] = 2
            modules["postgres"]["max_connections"] = 500
        if "redpanda" in modules:
            modules["redpanda"]["brokers"] = 3
    elif scale == "large":
        if "postgres" in modules:
            modules["postgres"]["replicas"] = 3
            modules["postgres"]["max_connections"] = 1000
        if "redpanda" in modules:
            modules["redpanda"]["brokers"] = 3
            # Increase partitions for all topics
            if "topics" in modules["redpanda"]:
                for t in modules["redpanda"]["topics"]:
                    t["partitions"] = 12
    
    # 2. Access pattern optimizations
    if access == "read_heavy":
        if "dragonfly" in modules:
            modules["dragonfly"]["eviction_policy"] = "allkeys-lru"
            modules["dragonfly"]["maxmemory"] = "2gb" if scale != "small" else "512mb"
    elif access == "write_heavy":
        if "redpanda" in modules:
            # Optimize for throughput
            pass # (Future: drive specific env vars)
            
    # 3. Project type hints (Module additions)
    # (Future: add specific modules based on type if missing)


def build_blueprint(config: NikameConfig) -> Blueprint:
    """Build a resolved Blueprint from a validated NikameConfig.

    This is the main entry point for blueprint resolution. It:
    1. Discovers all available modules
    2. Extracts active modules from the config
    3. Resolves transitive dependencies
    4. Detects cycles and conflicts
    5. Topologically sorts the module graph
    6. Instantiates modules in correct order

    Args:
        config: Validated NikameConfig.

    Returns:
        Resolved Blueprint ready for composer consumption.

    Raises:
        NikameCycleError: If dependency graph has cycles.
        NikameModuleConflictError: If conflicting modules declared.
        NikameDependencyError: If a required dependency is not available.
    """
    # Step 1: Discover all registered modules
    discover_modules()
    all_registered = get_all_modules()
    _log.debug("Registered modules: %s", list(all_registered.keys()))

    # Step 2: Extract which modules the user's config activates
    active_module_configs = _extract_active_modules(config)
    
    # Step 2.1: Apply project optimizations
    _apply_project_optimizations(config, active_module_configs)
    
    # Step 2.5: Feature-to-module dependency resolution removed in v0.3.4.
    # Integrations and features are now triggered automatically by the Matrix Engine
    # based on the selected infrastructure modules.

    _log.debug("Active modules after feature resolution: %s", list(active_module_configs.keys()))

    # Step 3: Build the dependency graph
    graph: nx.DiGraph = nx.DiGraph()  # type: ignore[type-arg]

    for mod_name in active_module_configs:
        graph.add_node(mod_name)

    # Add dependency edges and resolve transitive deps
    to_process = list(active_module_configs.keys())
    processed: set[str] = set()

    while to_process:
        mod_name = to_process.pop(0)
        if mod_name in processed:
            continue
        processed.add(mod_name)

        mod_cls = get_module_class(mod_name)
        if mod_cls is None:
            _log.warning("Module '%s' not found in registry, skipping", mod_name)
            continue

        # Add dependency edges
        for dep_name in mod_cls.DEPENDENCIES:
            graph.add_node(dep_name)
            graph.add_edge(mod_name, dep_name)  # mod_name depends on dep_name

            # If dependency wasn't explicitly configured, add default config
            if dep_name not in active_module_configs:
                active_module_configs[dep_name] = {}
                to_process.append(dep_name)

        # Check for conflicts
        for conflict_name in mod_cls.CONFLICTS:
            if conflict_name in active_module_configs:
                raise NikameModuleConflictError(
                    f"Module '{mod_name}' conflicts with '{conflict_name}'. "
                    "Remove one of them from your config."
                )

    # Step 4: Detect cycles
    if not nx.is_directed_acyclic_graph(graph):
        cycles = list(nx.simple_cycles(graph))
        raise NikameCycleError(
            f"Circular dependency detected in module graph: {cycles}"
        )

    # Step 5: Topological sort (reversed because edges point to deps)
    try:
        sorted_names = list(reversed(list(nx.topological_sort(graph))))
    except nx.NetworkXUnfeasible as exc:
        raise NikameCycleError(
            f"Cannot resolve module order: {exc}"
        ) from exc

    # Step 6: Identify and resolve port conflicts for local dev
    host_port_map: dict[str, int] = {}
    if config.environment.target == "local":
        # 1. Instantiate temporary modules to collect port requirements
        # We need a temporary context for this
        temp_ctx = ModuleContext(
            project_name=config.name,
            environment="local",
        )
        
        all_required_ports: dict[str, int] = {}
        for mod_name in sorted_names:
            mod_cls = get_module_class(mod_name)
            if mod_cls:
                instance = mod_cls({}, temp_ctx)
                all_required_ports.update(instance.required_ports())

        # 2. Resolve conflicts
        used_ports: set[int] = set()
        # Sort by service name for deterministic allocation
        for svc_name, base_port in sorted(all_required_ports.items()):
            final_port = base_port
            while final_port in used_ports:
                final_port += 1
            host_port_map[svc_name] = final_port
            used_ports.add(final_port)

    # Step 7: Create module context
    ctx = ModuleContext(
        project_name=config.name,
        environment=config.environment.target,
        namespace=config.environment.profile,
        cloud=config.environment.cloud,
        domain=config.environment.domain,
        tls_enabled=bool(config.gateway and config.gateway.tls.enabled),
        resource_tier="medium",
        features=config.features,
        active_modules=list(sorted_names),
        host_port_map=host_port_map,
    )

    # Step 7: Instantiate modules in sorted order
    modules: list[BaseModule] = []
    all_env_vars: dict[str, str] = {}
    warnings: list[str] = []

    for mod_name in sorted_names:
        mod_cls = get_module_class(mod_name)
        if mod_cls is None:
            _log.warning("Module '%s' in graph but not registered, skipping", mod_name)
            continue

        mod_config = active_module_configs.get(mod_name, {})
        instance = mod_cls(mod_config, ctx)
        modules.append(instance)

        # Collect env vars
        mod_env = instance.env_vars()
        all_env_vars.update(mod_env)

    # Store accumulated env vars in context
    ctx.all_env_vars = all_env_vars

    console.print(
        f"[success]✓ Blueprint resolved: {len(modules)} modules[/success]"
    )
    for mod in modules:
        console.print(f"  [module]{mod.NAME}[/module] ({mod.CATEGORY}) v{mod.version}")

    return Blueprint(
        project_name=config.name,
        modules=modules,
        graph=graph,
        config=config,
        warnings=warnings,
        env_vars=all_env_vars,
        features=config.features,
    )
