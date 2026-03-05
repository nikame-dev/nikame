"""Temporal workflow orchestration module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class TemporalModule(BaseModule):
    """Temporal workflow orchestration module."""

    NAME = "temporal"
    CATEGORY = "messaging"
    DESCRIPTION = "Temporal open-source durable execution platform"
    DEFAULT_VERSION = "1.23"
    DEPENDENCIES: list[str] = ["postgres"]  # Needs a database

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Temporal."""
        return {
            "temporal": {
                "image": f"temporalio/auto-setup:{self.version}",
                "restart": "unless-stopped",
                "ports": ["7233:7233", "8080:8080"],
                "environment": {
                    "DB": "postgresql",
                    "DB_PORT": "5432",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PWD": "${POSTGRES_PASSWORD}",
                    "POSTGRES_SEEDS": "postgres",
                    "DYNAMIC_CONFIG_FILE_PATH": "config/dynamicconfig/development.yaml",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "depends_on": ["postgres"],
            },
            "temporal-ui": {
                "image": "temporalio/ui:1.23.0",
                "restart": "unless-stopped",
                "ports": ["8082:8080"],
                "environment": {
                    "TEMPORAL_ADDRESS": "temporal:7233",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "depends_on": ["temporal"],
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Temporal."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "temporal", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "temporal"}},
                    "template": {
                        "metadata": {"labels": {"app": "temporal"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "temporal",
                                    "image": f"temporalio/auto-setup:{self.version}",
                                    "ports": [{"containerPort": 7233}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def env_vars(self) -> dict[str, str]:
        """Expose TEMPORAL_URL."""
        return {"TEMPORAL_URL": "temporal:7233"}
