"""ZenML orchestration module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class ZenMLModule(BaseModule):
    """ZenML orchestrator module.

    Configures ZenML Server backed by PostgreSQL.
    """

    NAME = "zenml"
    CATEGORY = "ml"
    DESCRIPTION = "ZenML MLOps pipeline orchestration"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 8237
    DEPENDENCIES = ["postgres"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested ZenML port."""
        return {"zenml": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for ZenML."""
        project = self.ctx.project_name
        return {
            "zenml": {
                "image": f"zenmldocker/zenml-server:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('zenml', self.port)}:8237"],
                "environment": {
                    "ZENML_STORE_URL": "postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@postgres:5432/zenml",
                    "ZENML_DEBUG": "false",
                    "ZENML_ANALYTICS_OPT_IN": "false",
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
                    "nikame.module": "zenml",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for ZenML."""
        name = "zenml"
        image = f"zenmldocker/zenml-server:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=8237,
                env={
                    "ZENML_STORE_URL": "$(DATABASE_URL)",
                    "ZENML_DEBUG": "false",
                    "ZENML_ANALYTICS_OPT_IN": "false",
                }
            ),
            self.service(name, port=8237, target_port=8237),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"zenml.{self.ctx.domain}", service_port=8237)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """ZenML server health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8237/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose ZenML Server URL to apps."""
        return {
            "ZENML_SERVER_URL": f"http://zenml:{self.port}",
        }


