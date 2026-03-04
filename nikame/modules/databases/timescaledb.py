"""TimescaleDB time-series module (Postgres extension)."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class TimescaleDBModule(BaseModule):
    """TimescaleDB module (Postgres with timescale extension)."""

    NAME = "timescaledb"
    CATEGORY = "database"
    DESCRIPTION = "TimescaleDB time-series database based on PostgreSQL"
    DEFAULT_VERSION = "latest-pg16"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for TimescaleDB."""
        return {
            "timescaledb": {
                "image": f"timescale/timescaledb:{self.version}",
                "restart": "unless-stopped",
                "ports": ["5433:5432"],
                "environment": {
                    "POSTGRES_PASSWORD": "${TIMESCALEDB_PASSWORD}",
                },
                "volumes": ["timescaledb_data:/var/lib/postgresql/data"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s StatefulSet for TimescaleDB."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {"name": "timescaledb", "namespace": self.ctx.namespace},
                "spec": {
                    "replicas": 1,
                    "serviceName": "timescaledb",
                    "selector": {"matchLabels": {"app": "timescaledb"}},
                    "template": {
                        "metadata": {"labels": {"app": "timescaledb"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "timescaledb",
                                    "image": f"timescale/timescaledb:{self.version}",
                                    "ports": [{"containerPort": 5432}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Timescaledb health check."""
        return {
            "test": ["CMD", "pg_isready", "-U", "postgres"],
            "interval": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose TIMESCALEDB_URL."""
        return {"TIMESCALEDB_URL": "postgres://postgres:${TIMESCALEDB_PASSWORD}@timescaledb:5432/postgres"}
