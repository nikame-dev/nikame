"""Gitea git hosting module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class GiteaModule(BaseModule):
    """Gitea git hosting module."""

    NAME = "gitea"
    CATEGORY = "cicd"
    DESCRIPTION = "Gitea self-hosted Git service"
    DEFAULT_VERSION = "1.21"
    DEPENDENCIES: list[str] = ["postgres"]

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Gitea."""
        return {
            "gitea": {
                "image": f"gitea/gitea:{self.version}",
                "restart": "unless-stopped",
                "ports": ["3000:3000", "2222:22"],
                "environment": {
                    "GITEA__database__DB_TYPE": "postgres",
                    "GITEA__database__HOST": "postgres:5432",
                    "GITEA__database__NAME": "gitea",
                    "GITEA__database__USER": "postgres",
                    "GITEA__database__PASSWD": "${POSTGRES_PASSWORD}",
                },
                "volumes": ["gitea_data:/data"],
                "networks": [f"{self.ctx.project_name}_network"],
                "depends_on": ["postgres"],
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Gitea."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "gitea", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "gitea"}},
                    "template": {
                        "metadata": {"labels": {"app": "gitea"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "gitea",
                                    "image": f"gitea/gitea:{self.version}",
                                    "ports": [{"containerPort": 3000}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def env_vars(self) -> dict[str, str]:
        """Expose GITEA_URL."""
        return {"GITEA_URL": "http://gitea:3000"}
