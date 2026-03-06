"""Redis in-memory data store module.

Used as a database with persistence. For cache use cases, NIKAME
recommends Dragonfly instead (25x memory efficiency).
"""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class RedisModule(BaseModule):
    """Redis database module with optional persistence.

    NIKAME will warn users to consider Dragonfly for cache workloads,
    but respects explicit choice of Redis.
    """

    NAME = "redis"
    CATEGORY = "database"
    DESCRIPTION = "Redis in-memory data store with optional persistence"
    DEFAULT_VERSION = "7"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.maxmemory: str = config.get("maxmemory", "256mb")
        self.persistence: bool = config.get("persistence", True)

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Redis."""
        cmd_parts = [
            "redis-server",
            "--maxmemory", self.maxmemory,
            "--maxmemory-policy", "allkeys-lru",
        ]
        if self.persistence:
            cmd_parts.extend(["--appendonly", "yes"])

        volumes = []
        if self.persistence:
            volumes.append("redis_data:/data")

        return {
            "redis": {
                "image": f"redis:{self.version}-alpine",
                "restart": "unless-stopped",
                "command": " ".join(cmd_parts),
                "ports": [f"{self.ctx.host_port_map.get('redis', 6379)}:6379"] if self.ctx.environment == "local" else [],
                "volumes": volumes,
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "redis",
                    "nikame.category": "database",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate full production-ready K8s architecture for Redis."""
        name = "redis"
        image = f"redis:{self.version}-alpine"

        # 1. StatefulSet
        ss = self.stateful_set(
            name=name,
            image=image,
            port=6379,
            pvc_name=f"{name}-data",
            pvc_size="5Gi",
            liveness_probe={"exec": {"command": ["redis-cli", "ping"]}, "initialDelaySeconds": 10}
        )

        # 2. Service
        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name, "namespace": self.ctx.namespace, "labels": {"app": name}},
            "spec": {
                "selector": {"app": name},
                "ports": [{"port": 6379, "targetPort": 6379}],
            },
        }

        # 3. Production Manifests
        manifests = [
            self.service_account(name),
            ss,
            service,
            self.network_policy(name, allow_from=["api", "worker"]),
            self.pdb(name, min_available=1),
        ]

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Redis readiness check."""
        return {
            "test": ["CMD", "redis-cli", "ping"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
            "start_period": "5s",
        }

    def env_vars(self) -> dict[str, str]:
        """Redis connection env vars."""
        return {
            "REDIS_URL": "redis://redis:6379/0",
            "REDIS_HOST": "redis",
            "REDIS_PORT": "6379",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for Redis."""
        return [
            {
                "alert": "RedisDown",
                "expr": "up{job='redis'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "Redis is down"},
            },
            {
                "alert": "RedisHighMemory",
                "expr": "redis_memory_used_bytes / redis_memory_max_bytes > 0.9",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Redis memory usage above 90%"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for Redis."""
        return {
            "title": f"{self.ctx.project_name} — Redis",
            "uid": "nikame-redis",
            "panels": [
                {"title": "Memory Usage", "type": "gauge", "targets": [{"expr": "redis_memory_used_bytes"}]},
                {"title": "Connected Clients", "type": "stat", "targets": [{"expr": "redis_connected_clients"}]},
                {"title": "Commands/sec", "type": "timeseries", "targets": [{"expr": "rate(redis_commands_processed_total[5m])"}]},
                {"title": "Hit Rate", "type": "stat", "targets": [{"expr": "redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)"}]},
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cost."""
        return 15.0
