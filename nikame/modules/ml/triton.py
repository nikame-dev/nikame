"""NVIDIA Triton Inference Server module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class TritonModule(BaseModule):
    """Triton Inference Server module.

    Configures a high-performance NVIDIA Triton server for model serving.
    """

    NAME = "triton"
    CATEGORY = "ml"
    DESCRIPTION = "NVIDIA Triton Inference Server"
    DEFAULT_VERSION = "24.03-py3"
    DEFAULT_PORT = 8000

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.grpc_port = config.get("grpc_port", 8001)
        self.metrics_port = config.get("metrics_port", 8002)

    def required_ports(self) -> dict[str, int]:
        """Requested Triton ports."""
        return {
            "triton-http": self.port,
            "triton-grpc": self.grpc_port,
            "triton-metrics": self.metrics_port,
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Triton."""
        project = self.ctx.project_name
        return {
            "triton": {
                "image": f"nvcr.io/nvidia/tritonserver:{self.version}",
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('triton-http', self.port)}:8000",
                    f"{self.ctx.host_port_map.get('triton-grpc', self.grpc_port)}:8001",
                    f"{self.ctx.host_port_map.get('triton-metrics', self.metrics_port)}:8002",
                ],
                "command": "tritonserver --model-repository=/models",
                "volumes": ["triton_models:/models"],
                # NVIDIA GPU Support
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
                    "nikame.module": "triton",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Triton."""
        name = "triton"
        image = f"nvcr.io/nvidia/tritonserver:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=8000,
                command=["tritonserver", "--model-repository=/models"],
            ),
            # In complete setup we should expose gRPC and metrics to K8s as well
            self.service(name, port=8000, target_port=8000),
        ]

        # Add grpc service
        grpc_service = self.service(f"{name}-grpc", port=8001, target_port=8001)
        manifests.append(grpc_service)

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"triton.{self.ctx.domain}", service_port=8000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Triton health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/v2/health/ready"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Triton endpoints to apps."""
        return {
            "TRITON_HTTP_URL": f"http://triton:{self.port}",
            "TRITON_GRPC_URL": f"triton:{self.grpc_port}",
        }


