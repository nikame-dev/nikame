"""Faster Whisper API module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class WhisperModule(BaseModule):
    """Faster Whisper API module.

    Configures an OpenAI-compatible API for speech-to-text transcription.
    """

    NAME = "whisper"
    CATEGORY = "ml"
    DESCRIPTION = "Faster Whisper API (Speech-to-Text)"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 8000

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Whisper port."""
        return {"whisper": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Whisper."""
        project = self.ctx.project_name
        return {
            "whisper": {
                "image": f"onerahmet/openai-whisper-api:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('whisper', self.port)}:8000"],
                "environment": {
                    "ASR_MODEL": "base",
                    "ASR_ENGINE": "faster_whisper",
                },
                "volumes": ["whisper_models:/root/.cache/whisper"],
                # NVIDIA GPU Support Highly Recommended
                "deploy": {
                    "resources": {
                        "reservations": {
                            "devices": [
                                {
                                    "driver": "nvidia",
                                    "count": "1",
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
                    "nikame.module": "whisper",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Whisper."""
        name = "whisper"
        image = f"onerahmet/openai-whisper-api:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=8000,
                env={
                    "ASR_MODEL": "base",
                    "ASR_ENGINE": "faster_whisper",
                }
            ),
            self.service(name, port=8000, target_port=8000),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"whisper.{self.ctx.domain}", service_port=8000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Whisper API health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/docs"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Whisper endpoint."""
        return {
            "WHISPER_URL": f"http://whisper:{self.port}",
        }


register_module(WhisperModule)
