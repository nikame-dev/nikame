"""Dragonfly cache module — NIKAME recommended alternative to Redis.

Dragonfly is a modern Redis-compatible in-memory store that uses
25x less memory than Redis for equivalent workloads, making it
the NIKAME smart default for cache workloads.
"""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class DragonflyModule(BaseModule):
    """Dragonfly in-memory cache module.

    Redis-compatible API with 25x memory efficiency. NIKAME's
    recommended default cache. Uses multi-threaded architecture
    with shared-nothing approach for high throughput.
    """

    NAME = "dragonfly"
    CATEGORY = "cache"
    DESCRIPTION = "Dragonfly — Redis-compatible cache with 25x memory efficiency"
    DEFAULT_VERSION = "latest"
    DEPENDENCIES: list[str] = []
    CONFLICTS = ["cache.redis"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.maxmemory: str = config.get("maxmemory", "1gb")
        self.eviction_policy: str = config.get("eviction_policy", "allkeys-lru")

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Dragonfly."""
        return {
            "dragonfly": {
                "image": f"docker.dragonflydb.io/dragonflydb/dragonfly:{self.version}",
                "restart": "unless-stopped",
                "ulimits": {"memlock": -1},
                "command": f"--maxmemory={self.maxmemory} --cache_mode=true",
                "ports": ["6379:6379"] if self.ctx.environment == "local" else [],
                "volumes": ["dragonfly_data:/data"],
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "dragonfly",
                    "nikame.category": "cache",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s Deployment + Service for Dragonfly."""
        deployment: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "dragonfly",
                "namespace": self.ctx.namespace,
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "dragonfly"}},
                "template": {
                    "metadata": {"labels": {"app": "dragonfly"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "dragonfly",
                                "image": f"docker.dragonflydb.io/dragonflydb/dragonfly:{self.version}",
                                "ports": [{"containerPort": 6379}],
                                "args": [f"--maxmemory={self.maxmemory}", "--cache_mode=true"],
                                "resources": self.resource_requirements(),
                            }
                        ]
                    },
                },
            },
        }

        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "dragonfly", "namespace": self.ctx.namespace},
            "spec": {
                "selector": {"app": "dragonfly"},
                "ports": [{"port": 6379, "targetPort": 6379}],
            },
        }

        return [deployment, service]

    def health_check(self) -> dict[str, Any]:
        """Dragonfly readiness check (Redis-compatible protocol)."""
        return {
            "test": ["CMD", "redis-cli", "ping"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
            "start_period": "5s",
        }

    def env_vars(self) -> dict[str, str]:
        """Cache connection env vars (Redis-compatible)."""
        return {
            "CACHE_URL": "redis://dragonfly:6379/0",
            "REDIS_URL": "redis://dragonfly:6379/0",
            "CACHE_HOST": "dragonfly",
            "CACHE_PORT": "6379",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for Dragonfly."""
        return [
            {
                "alert": "DragonflyDown",
                "expr": "up{job='dragonfly'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "Dragonfly is down"},
            },
            {
                "alert": "DragonflyHighMemory",
                "expr": "dragonfly_memory_used_bytes / dragonfly_memory_max_bytes > 0.9",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Dragonfly memory usage above 90%"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for Dragonfly."""
        return {
            "title": f"{self.ctx.project_name} — Dragonfly",
            "uid": "nikame-dragonfly",
            "panels": [
                {"title": "Memory Usage", "type": "gauge", "targets": [{"expr": "dragonfly_memory_used_bytes"}]},
                {"title": "Connected Clients", "type": "stat", "targets": [{"expr": "dragonfly_connected_clients"}]},
                {"title": "Commands/sec", "type": "timeseries", "targets": [{"expr": "rate(dragonfly_commands_processed_total[5m])"}]},
                {"title": "Cache Hit Rate", "type": "stat", "targets": [{"expr": "dragonfly_keyspace_hits / (dragonfly_keyspace_hits + dragonfly_keyspace_misses)"}]},
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Dragonfly is much cheaper than Redis equivalent."""
        return 8.0
