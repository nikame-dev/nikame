"""NATS messaging module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class NATSModule(BaseModule):
    """NATS messaging system module."""

    NAME = "nats"
    CATEGORY = "messaging"
    DESCRIPTION = "NATS cloud native messaging system"
    DEFAULT_VERSION = "2.10"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for NATS."""
        return {
            "nats": {
                "image": f"nats:{self.version}",
                "restart": "unless-stopped",
                "ports": ["4222:4222", "8222:8222"],
                "command": "-js",
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for NATS."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "nats", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "nats"}},
                    "template": {
                        "metadata": {"labels": {"app": "nats"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "nats",
                                    "image": f"nats:{self.version}",
                                    "ports": [{"containerPort": 4222}],
                                    "args": ["-js"],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """NATS health check."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:8222/varz"],
            "interval": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose NATS_URL."""
        return {"NATS_URL": "nats://nats:4222"}
