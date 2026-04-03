"""BentoML serving module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class BentoMLModule(BaseModule):
    """BentoML serving module.

    Configures a BentoML runner for scalable AI model serving.
    """

    NAME = "bentoml"
    CATEGORY = "ml"
    DESCRIPTION = "BentoML scalable model serving framework"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 3000

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.bento_tag = config.get("path", "my_bento:latest")

    def required_ports(self) -> dict[str, int]:
        """Requested BentoML port."""
        return {"bentoml": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for BentoML."""
        project = self.ctx.project_name
        return {
            "bentoml": {
                # In a real environment, this image is built by the BentoML CLI
                # We use a placeholder here for the blueprint structure
                "image": self.bento_tag,
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('bentoml', self.port)}:3000"],
                "environment": {
                    "BENTOML_PORT": "3000",
                    "BENTOML_HOST": "0.0.0.0",
                },
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "bentoml",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for BentoML."""
        name = "bentoml"
        image = self.bento_tag

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=3000,
            ),
            self.service(name, port=3000, target_port=3000),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"bentoml.{self.ctx.domain}", service_port=3000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """BentoML Server health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:3000/livez"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose BentoML URL to apps."""
        return {
            "BENTOML_URL": f"http://bentoml:{self.port}",
        }


