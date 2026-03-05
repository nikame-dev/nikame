from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class LlamaCppModule(BaseModule):
    """
    llama.cpp serving module for CPU and low-VRAM GPU inference using GGUF.
    """

    NAME = "llamacpp"
    CATEGORY = "ml"
    DESCRIPTION = "Lightweight GGUF inference engine"
    DEFAULT_VERSION = "latest"

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.model_path = config.get("model_path")

    def compose_spec(self) -> dict[str, Any]:
        return {
            f"llamacpp-{self.ctx.project_name}": {
                "image": "ghcr.io/ggerganov/llama.cpp:server",
                "command": [
                    "-m", f"/models/{self.model_path}",
                    "--host", "0.0.0.0",
                    "--port", "8080",
                ],
                "volumes": [
                    "./models:/models",
                ],
                "ports": ["8080:8080"],
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
            }
        }

    def health_check(self) -> dict[str, Any]:
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }
