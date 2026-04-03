from nikame.modules.registry import register_module
from typing import Any

from nikame.modules.base import BaseModule


@register_module
class MLGatewayModule(BaseModule):
    """
    Unified ML Gateway using LiteLLM to provide an OpenAI-compatible API.
    """

    NAME = "ml-gateway"
    CATEGORY = "ml"
    DESCRIPTION = "Unified OpenAI-compatible gateway for all local models"
    DEFAULT_VERSION = "latest"

    def required_ports(self) -> dict[str, int]:
        """Standard ML Gateway port."""
        return {"ml-gateway": 8000}

    def compose_spec(self) -> dict[str, Any]:
        port = self.ctx.host_port_map.get("ml-gateway", 8000)
        return {
            "ml-gateway": {
                "image": "ghcr.io/berriai/litellm:main-latest",
                "volumes": [
                    "./configs/ml-gateway/config.yaml:/app/config.yaml:ro",
                ],
                "ports": [f"{port}:8000"],
                "depends_on": {
                    m: {"condition": "service_healthy"}
                    for m in self.config.get("model_services", [])
                },
                "networks": [f"{self.ctx.project_name}_network"],
            }
        }

    def health_check(self) -> dict[str, Any]:
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/health/readiness"],
            "interval": "15s",
            "timeout": "5s",
            "retries": 10,
        }

    def init_scripts(self) -> list[tuple[str, str]]:
        """Generate LiteLLM configuration."""
        model_list = []
        for model_svc in self.config.get("model_services", []):
            model_list.append({
                "model_name": model_svc,
                "litellm_params": {
                    "model": f"openai/{model_svc}",
                    "api_base": f"http://{model_svc}:8000/v1",
                    "api_key": "not-needed"
                }
            })
            
        import yaml
        config = {
            "model_list": model_list,
            "litellm_settings": {
                "drop_params": True,
                "set_fastapi_logging": True
            }
        }
        return [("config.yaml", yaml.dump(config))]

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []
