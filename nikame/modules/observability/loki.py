"""Grafana Loki logging module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class LokiModule(BaseModule):
    """Grafana Loki module."""

    NAME = "loki"
    CATEGORY = "observability"
    DESCRIPTION = "Grafana Loki log aggregation system"
    DEFAULT_VERSION = "2.9.0"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Loki."""
        return {
            "loki": {
                "image": f"grafana/loki:{self.version}",
                "restart": "unless-stopped",
                "ports": ["3100:3100"],
                "command": "-config.file=/etc/loki/local-config.yaml",
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Loki."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "loki", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "loki"}},
                    "template": {
                        "metadata": {"labels": {"app": "loki"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "loki",
                                    "image": f"grafana/loki:{self.version}",
                                    "ports": [{"containerPort": 3100}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Loki health check."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:3100/ready"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose LOKI_URL."""
        return {"LOKI_URL": "http://loki:3100"}
