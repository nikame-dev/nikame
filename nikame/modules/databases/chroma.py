"""Chroma vector database module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class ChromaModule(BaseModule):
    """Chroma vector database module.

    Configures a standalone Chroma instance for semantic search and embeddings.
    """

    NAME = "chroma"
    CATEGORY = "database"
    DESCRIPTION = "Chroma vector database"
    DEFAULT_VERSION = "0.4.24"
    DEFAULT_PORT = 8000

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Chroma port."""
        return {
            "chroma": self.port,
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Chroma."""
        project = self.ctx.project_name
        return {
            "chroma": {
                "image": f"chromadb/chroma:{self.version}",
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('chroma', self.port)}:8000"
                ] if self.ctx.environment == "local" else [],
                "environment": {
                    "IS_PERSISTENT": "TRUE",
                    "PERSIST_DIRECTORY": "/chroma/chroma",
                },
                "volumes": ["chroma_data:/chroma/chroma"],
                "healthcheck": self.health_check(),
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "labels": {
                    "nikame.module": "chroma",
                    "nikame.category": "database",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Chroma."""
        name = "chroma"
        image = f"chromadb/chroma:{self.version}"

        manifests = [
            self.service_account(name),
            self.stateful_set(
                name=name,
                image=image,
                port=8000,
                pvc_name=f"{name}-data",
                pvc_size="10Gi",
                env_from=[{"configMapRef": {"name": f"{name}-config"}}],
                liveness_probe=self.health_check(),
            ),
            self.config_map(
                name=f"{name}-config",
                data={
                    "IS_PERSISTENT": "TRUE",
                    "PERSIST_DIRECTORY": "/chroma/chroma",
                }
            ),
            self.service(name, port=8000, target_port=8000),
        ]

        if self.ctx.environment == "local":
            manifests.append(self.node_port_service(name, port=8000, node_port=30081))

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Chroma health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/api/v1"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Chroma connection string to apps."""
        return {
            "CHROMA_URL": f"http://chroma:{self.port}",
        }


