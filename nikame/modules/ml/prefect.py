"""Prefect orchestration module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class PrefectModule(BaseModule):
    """Prefect orchestrator module.

    Configures Prefect Server backed by PostgreSQL.
    """

    NAME = "prefect"
    CATEGORY = "ml"
    DESCRIPTION = "Prefect dataflow and ML pipeline orchestration"
    DEFAULT_VERSION = "2-python3.11"
    DEFAULT_PORT = 4200
    DEPENDENCIES = ["postgres"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Prefect port."""
        return {"prefect": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Prefect."""
        project = self.ctx.project_name
        return {
            "prefect": {
                "image": f"prefecthq/prefect:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('prefect', self.port)}:4200"],
                "environment": {
                    "PREFECT_SERVER_API_HOST": "0.0.0.0",
                    "PREFECT_API_URL": f"http://localhost:{self.port}/api",
                    "PREFECT_API_DATABASE_CONNECTION_URL": "postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@postgres:5432/prefect",
                },
                "command": "prefect server start --host 0.0.0.0",
                "depends_on": {
                    "postgres": {"condition": "service_healthy"},
                },
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "prefect",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Prefect."""
        name = "prefect"
        image = f"prefecthq/prefect:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=4200,
                command=["prefect", "server", "start", "--host", "0.0.0.0"],
                env={
                    "PREFECT_SERVER_API_HOST": "0.0.0.0",
                    "PREFECT_API_URL": "$(PREFECT_API_URL)",
                    "PREFECT_API_DATABASE_CONNECTION_URL": "$(DATABASE_URL)",
                }
            ),
            self.service(name, port=4200, target_port=4200),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"prefect.{self.ctx.domain}", service_port=4200)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Prefect server health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:4200/api/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Prefect API URL to apps."""
        return {
            "PREFECT_API_URL": f"http://prefect:{self.port}/api",
        }


