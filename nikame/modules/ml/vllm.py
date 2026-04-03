from nikame.modules.registry import register_module
from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class VLLMModule(BaseModule):
    """
    vLLM serving module for high-throughput LLM inference on NVIDIA GPUs.
    """

    NAME = "vllm"
    CATEGORY = "ml"
    DESCRIPTION = "High-efficiency LLM serving with PagedAttention"
    DEFAULT_VERSION = "latest"

    def required_ports(self) -> dict[str, int]:
        """Standard vLLM API port."""
        return {"vllm": 8000}

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.model = config.get("model")
        self.gpu_memory_util = config.get("gpu_memory_utilization", 0.9)
        self.tensor_parallel = config.get("tensor_parallel_size", 1)

    def compose_spec(self) -> dict[str, Any]:
        svc_name = self.config.get("name", f"vllm-{self.ctx.project_name}")
        spec = {
            "image": f"vllm/vllm-openai:{self.version}",
            "command": [
                "--model", str(self.model),
                "--gpu-memory-utilization", str(self.gpu_memory_util),
                "--tensor-parallel-size", str(self.tensor_parallel),
            ],
            "ports": [f"{self.ctx.host_port_map.get('vllm', 8000)}:8000"] if self.ctx.environment == "local" else [],
            "healthcheck": self.health_check(),
            "networks": [f"{self.ctx.project_name}_network"],
        }

        if self.config.get("gpu", True) is True:
            spec["deploy"] = {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": "nvidia",
                                "count": self.tensor_parallel,
                                "capabilities": ["gpu"],
                            }
                        ]
                    }
                }
            }

        return {svc_name: spec}

    def health_check(self) -> dict[str, Any]:
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []
