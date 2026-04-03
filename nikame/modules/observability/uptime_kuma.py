"""Uptime Kuma monitoring module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule


@register_module
class UptimeKumaModule(BaseModule):
    """Uptime Kuma monitoring module."""

    NAME = "uptime_kuma"
    CATEGORY = "observability"
    DESCRIPTION = "Uptime Kuma self-hosted monitoring tool"
    DEFAULT_VERSION = "1.23.11"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Uptime Kuma."""
        return {
            "uptime-kuma": {
                "image": f"louislam/uptime-kuma:{self.version}",
                "restart": "unless-stopped",
                "ports": ["3001:3001"],
                "volumes": ["uptime_kuma_data:/app/data"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Uptime Kuma."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "uptime-kuma", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "uptime-kuma"}},
                    "template": {
                        "metadata": {"labels": {"app": "uptime-kuma"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "uptime-kuma",
                                    "image": f"louislam/uptime-kuma:{self.version}",
                                    "ports": [{"containerPort": 3001}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Uptime Kuma health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:3001"],
            "interval": "30s",
        }
