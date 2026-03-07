from typing import Any

from nikame.modules.base import BaseModule


class ModelDownloaderModule(BaseModule):
    """
    One-time init job to download ML models from HuggingFace/Ollama.
    """

    NAME = "model-downloader"
    CATEGORY = "ml"
    DESCRIPTION = "Automated model downloader and quantizer"
    DEFAULT_VERSION = "latest"

    def compose_spec(self) -> dict[str, Any]:
        return {
            "model-downloader": {
                "image": "python:3.11-slim",
                "command": ["python", "-c", "print('Downloading models...')"], # Placeholder
                "volumes": [
                    "model_cache:/root/.nikame/models",
                ],
                "networks": [f"{self.ctx.project_name}_network"],
            }
        }

    def health_check(self) -> dict[str, Any]:
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []
