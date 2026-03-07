"""Woodpecker CI module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class WoodpeckerModule(BaseModule):
    """Woodpecker CI module."""

    NAME = "woodpecker"
    CATEGORY = "cicd"
    DESCRIPTION = "Woodpecker CI server and agent"
    DEFAULT_VERSION = "2.4"

    def required_ports(self) -> dict[str, int]:
        """Ports for Woodpecker Server."""
        return {"woodpecker": 8081}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Woodpecker CI."""
        return {
            "woodpecker-server": {
                "image": f"woodpeckerci/woodpecker-server:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('woodpecker', 8081)}:8000"] if self.ctx.environment == "local" else [],
                "environment": {
                    "WOODPECKER_OPEN": "true",
                    "WOODPECKER_HOST": "http://localhost:8081",
                },
                "networks": [f"{self.ctx.project_name}_network"],
            },
            "woodpecker-agent": {
                "image": f"woodpeckerci/woodpecker-agent:{self.version}",
                "restart": "unless-stopped",
                "environment": {
                    "WOODPECKER_SERVER": "woodpecker-server:9000",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "depends_on": ["woodpecker-server"],
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Woodpecker."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "woodpecker", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "woodpecker"}},
                    "template": {
                        "metadata": {"labels": {"app": "woodpecker"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "woodpecker",
                                    "image": f"woodpeckerci/woodpecker-server:{self.version}",
                                    "ports": [{"containerPort": 8000}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Woodpecker health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/healthz"],
            "interval": "30s",
        }
