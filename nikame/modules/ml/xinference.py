"""Xinference model serving module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class XinferenceModule(BaseModule):
    """Xinference serving module.

    Configures Xinference for running LLMs, embedding models, and audio models.
    """

    NAME = "xinference"
    CATEGORY = "ml"
    DESCRIPTION = "Xorbits Inference (Xinference) serving engine"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 9997

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Xinference port."""
        return {"xinference": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Xinference."""
        project = self.ctx.project_name
        return {
            "xinference": {
                "image": f"xorbits/xinference:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('xinference', self.port)}:9997"],
                "environment": {
                    "XINFERENCE_HOME": "/data",
                },
                "volumes": ["xinference_data:/data"],
                "command": "xinference-local -H 0.0.0.0 -p 9997",
                # NVIDIA GPU Support Highly Recommended
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
                    "nikame.module": "xinference",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Xinference."""
        name = "xinference"
        image = f"xorbits/xinference:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=9997,
                command=["xinference-local", "-H", "0.0.0.0", "-p", "9997"],
                env={
                    "XINFERENCE_HOME": "/data",
                }
            ),
            self.service(name, port=9997, target_port=9997),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"xinference.{self.ctx.domain}", service_port=9997)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Xinference health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:9997/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Xinference endpoint."""
        return {
            "XINFERENCE_URL": f"http://xinference:{self.port}",
        }


