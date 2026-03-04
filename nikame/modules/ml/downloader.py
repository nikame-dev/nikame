from typing import Any
from nikame.modules.base import BaseModule, ModuleContext


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
