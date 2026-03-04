"""Authentik identity provider module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class AuthentikModule(BaseModule):
    """Authentik identity provider module."""

    NAME = "authentik"
    CATEGORY = "auth"
    DESCRIPTION = "Authentik unified identity provider"
    DEFAULT_VERSION = "2024.2"
    DEPENDENCIES: list[str] = ["postgres", "redis"]

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Authentik."""
        return {
            "authentik-server": {
                "image": f"ghcr.io/goauthentik/server:{self.version}",
                "restart": "unless-stopped",
                "command": "server",
                "environment": {
                    "AUTHENTIK_REDIS__HOST": "redis",
                    "AUTHENTIK_POSTGRESQL__HOST": "postgres",
                    "AUTHENTIK_POSTGRESQL__USER": "postgres",
                    "AUTHENTIK_POSTGRESQL__NAME": "authentik",
                    "AUTHENTIK_POSTGRESQL__PASSWORD": "${POSTGRES_PASSWORD}",
                    "AUTHENTIK_SECRET_KEY": "${AUTHENTIK_SECRET_KEY}",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "depends_on": ["postgres", "redis"],
            },
            "authentik-worker": {
                "image": f"ghcr.io/goauthentik/server:{self.version}",
                "restart": "unless-stopped",
                "command": "worker",
                "environment": {
                    "AUTHENTIK_REDIS__HOST": "redis",
                    "AUTHENTIK_POSTGRESQL__HOST": "postgres",
                    "AUTHENTIK_POSTGRESQL__USER": "postgres",
                    "AUTHENTIK_POSTGRESQL__NAME": "authentik",
                    "AUTHENTIK_POSTGRESQL__PASSWORD": "${POSTGRES_PASSWORD}",
                    "AUTHENTIK_SECRET_KEY": "${AUTHENTIK_SECRET_KEY}",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "depends_on": ["postgres", "redis"],
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Authentik."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "authentik", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "authentik"}},
                    "template": {
                        "metadata": {"labels": {"app": "authentik"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "server",
                                    "image": f"ghcr.io/goauthentik/server:{self.version}",
                                    "ports": [{"containerPort": 9000}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def env_vars(self) -> dict[str, str]:
        """Expose AUTHENTIK_URL."""
        return {"AUTHENTIK_URL": "http://authentik-server:9000"}
