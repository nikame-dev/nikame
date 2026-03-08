"""LangFuse LLM Tracing module."""

from __future__ import annotations

from typing import Any
import secrets

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class LangFuseModule(BaseModule):
    """LangFuse module for LLM Observability and Tracing.

    Configures LangFuse server using Postgres for storage.
    """

    NAME = "langfuse"
    CATEGORY = "ml"
    DESCRIPTION = "LangFuse LLM observability and tracing"
    DEFAULT_VERSION = "2"
    DEFAULT_PORT = 3000
    DEPENDENCIES = ["postgres"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        
        # Determine secrets: Check environment or generate local ones
        self.nextauth_url = config.get("nextauth_url", f"http://localhost:{self.port}")
        self.salt = "langfuse-salt-placeholder"
        self.nextauth_secret = "langfuse-secret-placeholder"
        
        # Telemetry is opted out by default
        self.telemetry_enabled = config.get("telemetry_enabled", False)

    def required_ports(self) -> dict[str, int]:
        """Requested LangFuse port."""
        return {"langfuse": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for LangFuse."""
        project = self.ctx.project_name
        return {
            "langfuse": {
                "image": f"ghcr.io/langfuse/langfuse:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('langfuse', self.port)}:3000"],
                "environment": {
                    "NEXTAUTH_URL": self.nextauth_url,
                    "NEXTAUTH_SECRET": self.nextauth_secret,
                    "SALT": self.salt,
                    "DATABASE_URL": "postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@postgres:5432/langfuse",
                    "TELEMETRY_ENABLED": "true" if self.telemetry_enabled else "false",
                    "NODE_ENV": "production",
                },
                "depends_on": {
                    "postgres": {"condition": "service_healthy"},
                },
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "langfuse",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for LangFuse."""
        name = "langfuse"
        image = f"ghcr.io/langfuse/langfuse:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=3000,
                env={
                    "NEXTAUTH_URL": self.nextauth_url,
                    "NEXTAUTH_SECRET": self.nextauth_secret,
                    "SALT": self.salt,
                    "DATABASE_URL": "$(DATABASE_URL)",
                    "TELEMETRY_ENABLED": "true" if self.telemetry_enabled else "false",
                    "NODE_ENV": "production",
                }
            ),
            self.service(name, port=3000, target_port=3000),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"langfuse.{self.ctx.domain}", service_port=3000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """LangFuse health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:3000/api/public/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 5,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose LangFuse host URL to apps."""
        return {
            "LANGFUSE_HOST": f"http://langfuse:{self.port}",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-placeholder",
            "LANGFUSE_SECRET_KEY": "sk-lf-placeholder",
        }


register_module(LangFuseModule)
