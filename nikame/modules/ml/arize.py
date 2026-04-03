"""Arize Phoenix module for LLM Observability."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class PhoenixModule(BaseModule):
    """Arize Phoenix module for LLM observability and evaluation.

    Configures Phoenix server to collect traces and display them.
    """

    NAME = "arize-phoenix"
    CATEGORY = "ml"
    DESCRIPTION = "Arize Phoenix LLM observability and tracing"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 6006

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Phoenix port."""
        return {"phoenix": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Phoenix."""
        project = self.ctx.project_name
        return {
            "phoenix": {
                "image": f"arizephoenix/phoenix:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('phoenix', self.port)}:6006"],
                "environment": {
                    "PHOENIX_PORT": "6006",
                    "PHOENIX_HOST": "0.0.0.0",
                },
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "arize-phoenix",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Phoenix."""
        name = "phoenix"
        image = f"arizephoenix/phoenix:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=6006,
                env={
                    "PHOENIX_PORT": "6006",
                    "PHOENIX_HOST": "0.0.0.0",
                }
            ),
            self.service(name, port=6006, target_port=6006),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"phoenix.{self.ctx.domain}", service_port=6006)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Phoenix health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:6006/"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Phoenix collector URL to apps."""
        return {
            "PHOENIX_COLLECTOR_ENDPOINT": f"http://phoenix:{self.port}/v1/traces",
        }


