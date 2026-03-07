"""ClickHouse OLAP database module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class ClickHouseModule(BaseModule):
    """ClickHouse columnar database module."""

    NAME = "clickhouse"
    CATEGORY = "database"
    DESCRIPTION = "ClickHouse fast open-source OLAP database management system"
    DEFAULT_VERSION = "24.1"

    def required_ports(self) -> dict[str, int]:
        """Ports for ClickHouse HTTP and Native."""
        return {
            "clickhouse": 8123,
            "clickhouse-native": 9000,
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for ClickHouse."""
        return {
            "clickhouse": {
                "image": f"clickhouse/clickhouse-server:{self.version}",
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('clickhouse', 8123)}:8123",
                    f"{self.ctx.host_port_map.get('clickhouse-native', 9000)}:9000"
                ] if self.ctx.environment == "local" else [],
                "ulimits": {"nofile": {"soft": 262144, "hard": 262144}},
                "volumes": ["clickhouse_data:/var/lib/clickhouse"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s StatefulSet for ClickHouse."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {"name": "clickhouse", "namespace": self.ctx.namespace},
                "spec": {
                    "replicas": 1,
                    "serviceName": "clickhouse",
                    "selector": {"matchLabels": {"app": "clickhouse"}},
                    "template": {
                        "metadata": {"labels": {"app": "clickhouse"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "clickhouse",
                                    "image": f"clickhouse/clickhouse-server:{self.version}",
                                    "ports": [{"containerPort": 8123}, {"containerPort": 9000}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """ClickHouse health check."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:8123/ping"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose CLICKHOUSE_HOST."""
        return {"CLICKHOUSE_HOST": "clickhouse", "CLICKHOUSE_PORT": "8123"}
