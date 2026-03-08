"""Text Generation Inference (TGI) serving module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class TGIModule(BaseModule):
    """Text Generation Inference module.

    Configures a HuggingFace TGI server for fast LLM deployment.
    """

    NAME = "tgi"
    CATEGORY = "ml"
    DESCRIPTION = "HuggingFace Text Generation Inference (TGI) serving engine"
    DEFAULT_VERSION = "2.0"
    DEFAULT_PORT = 8080

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        
        # In a real environment, this comes from the MLOps Config models array
        # Provide a safe default for development
        self.model_id = config.get("path", "HuggingFaceH4/zephyr-7b-beta")
        self.hf_token = config.get("token", "")

    def required_ports(self) -> dict[str, int]:
        """Requested TGI port."""
        return {"tgi": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for TGI."""
        project = self.ctx.project_name
        return {
            "tgi": {
                "image": f"ghcr.io/huggingface/text-generation-inference:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('tgi', self.port)}:80"],
                "environment": {
                    "MODEL_ID": self.model_id,
                    "HF_TOKEN": self.hf_token,
                    "PORT": "80",
                },
                "volumes": ["hf_cache:/data"],
                # TGI supports GPU via nvidia runtime
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
                } if self.config.get("gpu", True) is True else {},
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "tgi",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for TGI."""
        name = "tgi"
        image = f"ghcr.io/huggingface/text-generation-inference:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=80,
                env={
                    "MODEL_ID": self.model_id,
                    "PORT": "80",
                    "HF_TOKEN": self.hf_token,
                }
            ),
            self.service(name, port=80, target_port=80),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"tgi.{self.ctx.domain}", service_port=80)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """TGI Server health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:80/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose TGI URL to apps."""
        return {
            "TGI_URL": f"http://tgi:{self.port}",
        }


register_module(TGIModule)
