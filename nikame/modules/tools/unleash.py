"""Unleash feature flag module for NIKAME.

Provides a managed feature flag server integrated with the project's infrastructure.
"""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext

@register_module
class UnleashModule(BaseModule):
    """Configuration for Unleash feature flag server."""

    NAME = "unleash"
    DESCRIPTION = "Enterprise feature flag management (managed Unleash server)"
    CATEGORY = "tools"
    DEPENDENCIES = ["postgres"]

    DEFAULT_VERSION = "5.11"
    DEFAULT_PORT = 4242

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port: int = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Unleash API and Dashboard port."""
        return {"unleash": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service for Unleash."""
        project = self.ctx.project_name
        
        # Unleash needs its own database or a separate schema.
        # For simplicity in local dev, we'll use a separate container or separate DB.
        # Here we'll configure it to use the project's Postgres but a different DB name.
        
        services: dict[str, Any] = {
            "unleash": {
                "image": "unleashorg/unleash-server:5.11",
                "restart": "unless-stopped",
                "environment": {
                    "DATABASE_HOST": "postgres",
                    "DATABASE_NAME": "unleash",
                    "DATABASE_USER": "${POSTGRES_USER:-postgres}",
                    "DATABASE_PASSWORD": "${POSTGRES_PASSWORD}",
                    "DATABASE_SSL": "false",
                    "UNLEASH_URL": f"http://localhost:{self.port}",
                    # Default admin token for local dev convenience
                    "INIT_FRONTEND_API_TOKENS": "*:*.default-token",
                    "INIT_CLIENT_API_TOKENS": "*:*.default-token",
                },
                "ports": [f"{self.ctx.host_port_map.get('unleash', self.port)}:{self.port}"],
                "depends_on": {
                    "postgres": {"condition": "service_healthy"}
                },
                "networks": [f"{project}_backend", f"{project}_data"],
                "labels": {
                    "nikame.module": "unleash",
                    "nikame.category": "tools",
                },
                "logging": {
                    "driver": "json-file",
                    "options": {
                        "max-size": "10m",
                        "max-file": "3"
                    }
                }
            }
        }
        
        return services

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Unleash K8s Deployment and Service."""
        name = "unleash"
        image = "unleashorg/unleash-server:5.11"
        
        manifests = [
            self.service_account(name),
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": name,
                    "namespace": self.ctx.namespace,
                    "labels": {"app": name}
                },
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": {"app": name}},
                    "template": {
                        "metadata": {"labels": {"app": name}},
                        "spec": {
                            "serviceAccountName": name,
                            "containers": [
                                {
                                    "name": name,
                                    "image": image,
                                    "ports": [{"containerPort": self.port}],
                                    "env": [
                                        {"name": "DATABASE_HOST", "value": "postgres"},
                                        {"name": "DATABASE_NAME", "value": "unleash"},
                                        {"name": "DATABASE_SSL", "value": "false"},
                                    ],
                                    "envFrom": [{"secretRef": {"name": "postgres-secret"}}],
                                    "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}},
                                }
                            ]
                        }
                    }
                }
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": name, "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"app": name},
                    "ports": [{"port": self.port, "targetPort": self.port}]
                }
            }
        ]
        return manifests

    def health_check(self) -> dict[str, Any]:
        """Unleash health check."""
        return {
            "test": ["CMD", "curl", "-f", f"http://localhost:{self.port}/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Unleash connection details."""
        return {
            "UNLEASH_API_URL": f"http://unleash:{self.port}/api",
            "UNLEASH_APP_NAME": self.ctx.project_name,
            "UNLEASH_ENVIRONMENT": self.ctx.environment,
            # Placeholder/Default token for initial setup
            "UNLEASH_API_TOKEN": "default-token",
        }

    def guide_metadata(self) -> dict[str, Any]:
        """Unleash-specific guide metadata."""
        port = self.ctx.host_port_map.get("unleash", self.port)
        return {
            "overview": self.DESCRIPTION,
            "urls": [
                {
                    "label": "Unleash Dashboard",
                    "url": f"http://localhost:{port}",
                    "usage": "Manage feature flags",
                    "creds": "admin / unleash4all"
                }
            ],
            "feature_guides": [
                {
                    "title": "Using Feature Flags",
                    "content": "NIKAME scaffolds a feature flag client in `app/core/features.py`. Use it to check for toggle states in your business logic."
                }
            ],
        }
