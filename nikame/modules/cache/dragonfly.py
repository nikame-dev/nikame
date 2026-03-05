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
        spec: dict[str, Any] = {
            "image": f"docker.dragonflydb.io/dragonflydb/dragonfly:{self.version}",
            "restart": "unless-stopped",
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
        
        # Only add ulimits in non-local environments or if explicitly requested
        # 'memlock' -1 often fails in local WSL/Docker environments
        if self.ctx.environment != "local":
            spec["ulimits"] = {"memlock": -1}
            
        return {"dragonfly": spec}


    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s StatefulSet + Service + HPA + PDB for Dragonfly."""
        name = "dragonfly"
        image = f"docker.dragonflydb.io/dragonflydb/dragonfly:{self.version}"
        
        # 1. StatefulSet
        ss = self.stateful_set(
            name=name,
            image=image,
            port=6379,
            pvc_name=f"{name}-data",
            pvc_size="10Gi",
            liveness_probe={
                "exec": {"command": ["redis-cli", "ping"]},
                "initialDelaySeconds": 10,
                "periodSeconds": 30,
            }
        )
        # Update args for Dragonfly
        ss["spec"]["template"]["spec"]["containers"][0]["args"] = [
            f"--maxmemory={self.maxmemory}", 
            "--cache_mode=true"
        ]

        # 2. Service
        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name, "namespace": self.ctx.namespace},
            "spec": {
                "selector": {"app": name},
                "ports": [{"port": 6379, "targetPort": 6379}],
            },
        }

        # 3. Production Manifests
        return [
            ss,
            service,
            self.hpa(name, min_reps=1, max_reps=3), # Dragonfly is vertically scalable but HPA is good for metrics
            self.pdb(name)
        ]

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
