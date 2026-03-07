"""Neo4j graph database module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class Neo4jModule(BaseModule):
    """Neo4j graph database module."""

    NAME = "neo4j"
    CATEGORY = "database"
    DESCRIPTION = "Neo4j graph database management system"
    DEFAULT_VERSION = "5.18.0"

    def required_ports(self) -> dict[str, int]:
        """Ports for Neo4j HTTP and Bolt."""
        return {
            "neo4j": 7474,
            "neo4j-bolt": 7687,
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Neo4j."""
        return {
            "neo4j": {
                "image": f"neo4j:{self.version}",
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('neo4j', 7474)}:7474",
                    f"{self.ctx.host_port_map.get('neo4j-bolt', 7687)}:7687"
                ] if self.ctx.environment == "local" else [],
                "environment": {
                    "NEO4J_AUTH": "neo4j/${NEO4J_PASSWORD}",
                },
                "volumes": ["neo4j_data:/data"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Neo4j."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "neo4j", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "neo4j"}},
                    "template": {
                        "metadata": {"labels": {"app": "neo4j"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "neo4j",
                                    "image": f"neo4j:{self.version}",
                                    "ports": [{"containerPort": 7474}, {"containerPort": 7687}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Neo4j health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:7474"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose NEO4J_URL."""
        return {"NEO4J_URL": "bolt://neo4j:7687"}
