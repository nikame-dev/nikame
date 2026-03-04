from typing import Any
from nikame.modules.base import BaseModule, ModuleContext


class MLGatewayModule(BaseModule):
    """
    Unified ML Gateway using LiteLLM to provide an OpenAI-compatible API.
    """

    NAME = "ml-gateway"
    CATEGORY = "ml"
    DESCRIPTION = "Unified OpenAI-compatible gateway for all local models"
    DEFAULT_VERSION = "latest"

    def compose_spec(self) -> dict[str, Any]:
        return {
            "ml-gateway": {
                "build": {
                    "context": "./services/ml-gateway",
                    "dockerfile": "Dockerfile",
                },
                "environment": {
                    "PORT": "8000",
                },
                "ports": ["8000:8000"],
                "depends_on": {
                    m: {"condition": "service_healthy"} 
                    for m in self.config.get("model_services", [])
                },
                "networks": [f"{self.ctx.project_name}_network"],
            }
        }
