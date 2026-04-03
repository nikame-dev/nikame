"""LocalAI serving module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class LocalAIModule(BaseModule):
    """LocalAI module.

    Configures LocalAI to act as a drop-in API replacement for OpenAI 
    using local models.
    """

    NAME = "localai"
    CATEGORY = "ml"
    DESCRIPTION = "LocalAI OpenAI-compatible API serving local models"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 8080

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.models_path = config.get("models_path", "/build/models")

    def required_ports(self) -> dict[str, int]:
        """Requested LocalAI port."""
        return {"localai": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for LocalAI."""
        project = self.ctx.project_name
        return {
            "localai": {
                "image": f"quay.io/go-skynet/local-ai:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('localai', self.port)}:8080"],
                "environment": {
                    "MODELS_PATH": "/build/models",
                    "DEBUG": "true",
                },
                "volumes": ["localai_models:/build/models"],
                # NVIDIA GPU Support Optional but good for performance
                "deploy": {
                    "resources": {
                        "reservations": {
                            "devices": [
                                {
                                    "driver": "nvidia",
                                    "count": "all",
                                    "capabilities": ["gpu"]
                                }
                            ]
                        }
                    }
                } if self.config.get("gpu", False) is True else {},
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "localai",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for LocalAI."""
        name = "localai"
        image = f"quay.io/go-skynet/local-ai:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=8080,
                env={
                    "MODELS_PATH": "/build/models",
                    "DEBUG": "true",
                }
            ),
            self.service(name, port=8080, target_port=8080),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"localai.{self.ctx.domain}", service_port=8080)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """LocalAI Server health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8080/readyz"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose LocalAI API compatible URL to apps."""
        return {
            "OPENAI_API_BASE": f"http://localai:{self.port}/v1",
        }


