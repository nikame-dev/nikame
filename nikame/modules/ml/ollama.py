from nikame.modules.registry import register_module
from typing import Any

from nikame.modules.base import BaseModule


@register_module
class OllamaModule(BaseModule):
    """
    Ollama serving module for easy LLM management and local inference.
    """

    NAME = "ollama"
    CATEGORY = "ml"
    DESCRIPTION = "Local LLM runner with simple API"
    DEFAULT_VERSION = "latest"

    def required_ports(self) -> dict[str, int]:
        """Standard Ollama API port."""
        return {"ollama": 11434}

    def compose_spec(self) -> dict[str, Any]:
        svc_name = self.config.get("name", f"ollama-{self.ctx.project_name}")
        spec = {
            "image": f"ollama/ollama:{self.version}",
            "volumes": [
                "ollama_data:/root/.ollama",
            ],
            "ports": [f"{self.ctx.host_port_map.get('ollama', 11434)}:11434"] if self.ctx.environment == "local" else [],
            "healthcheck": self.health_check(),
            "networks": [f"{self.ctx.project_name}_network"],
        }

        if self.config.get("gpu", False) is True:
            spec["deploy"] = {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": "nvidia",
                                "count": 1,
                                "capabilities": ["gpu"],
                            }
                        ]
                    }
                }
            }

        return {svc_name: spec}

    def health_check(self) -> dict[str, Any]:
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:11434/api/tags"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []
