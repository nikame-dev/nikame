"""Coqui TTS module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class TTSModule(BaseModule):
    """Coqui TTS API module.

    Configures a scalable Text-to-Speech serving engine.
    """

    NAME = "tts"
    CATEGORY = "ml"
    DESCRIPTION = "Coqui TTS API (Text-to-Speech)"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 5002

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested TTS port."""
        return {"tts": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for TTS."""
        project = self.ctx.project_name
        return {
            "tts": {
                "image": f"ghcr.io/coqui-ai/tts:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('tts', self.port)}:5002"],
                "environment": {
                    "TTS_MODEL": "tts_models/en/vctk/vits",
                },
                "volumes": ["tts_models:/root/.local/share/tts"],
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
                "command": "python3 TTS/server/server.py --list_models", 
                # Note: Command here is a placeholder for the blueprint
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "tts",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for TTS."""
        name = "tts"
        image = f"ghcr.io/coqui-ai/tts:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=5002,
                command=["python3", "TTS/server/server.py"],
                env={
                    "TTS_MODEL": "tts_models/en/vctk/vits",
                }
            ),
            self.service(name, port=5002, target_port=5002),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"tts.{self.ctx.domain}", service_port=5002)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """TTS API health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:5002/"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose TTS endpoint."""
        return {
            "TTS_URL": f"http://tts:{self.port}",
        }


register_module(TTSModule)
