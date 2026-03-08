"""Weaviate vector database module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class WeaviateModule(BaseModule):
    """Weaviate vector database module.

    Configures a standalone Weaviate instance for semantic search.
    """

    NAME = "weaviate"
    CATEGORY = "database"
    DESCRIPTION = "Weaviate vector database"
    DEFAULT_VERSION = "1.24.1"
    DEFAULT_PORT = 8080

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.grpc_port = config.get("grpc_port", 50051)

    def required_ports(self) -> dict[str, int]:
        """Requested Weaviate ports."""
        return {
            "weaviate": self.port,
            "weaviate-grpc": self.grpc_port
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Weaviate."""
        project = self.ctx.project_name
        return {
            "weaviate": {
                "image": f"semitechnologies/weaviate:{self.version}",
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('weaviate', self.port)}:8080",
                    f"{self.ctx.host_port_map.get('weaviate-grpc', self.grpc_port)}:50051",
                ] if self.ctx.environment == "local" else [],
                "environment": {
                    "QUERY_DEFAULTS_LIMIT": "25",
                    "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
                    "PERSISTENCE_DATA_PATH": "/var/lib/weaviate",
                    "DEFAULT_VECTORIZER_MODULE": "none",
                    "ENABLE_MODULES": "text2vec-openai,text2vec-cohere,text2vec-huggingface,generative-openai",
                    "CLUSTER_HOSTNAME": "node1",
                },
                "volumes": ["weaviate_data:/var/lib/weaviate"],
                "healthcheck": self.health_check(),
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "labels": {
                    "nikame.module": "weaviate",
                    "nikame.category": "database",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Weaviate."""
        name = "weaviate"
        image = f"semitechnologies/weaviate:{self.version}"

        manifests = [
            self.service_account(name),
            self.stateful_set(
                name=name,
                image=image,
                port=8080,
                pvc_name=f"{name}-data",
                pvc_size="10Gi",
                env_from=[{"configMapRef": {"name": f"{name}-config"}}],
                liveness_probe=self.health_check(),
            ),
            self.config_map(
                name=f"{name}-config",
                data={
                    "QUERY_DEFAULTS_LIMIT": "25",
                    "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
                    "PERSISTENCE_DATA_PATH": "/var/lib/weaviate",
                    "DEFAULT_VECTORIZER_MODULE": "none",
                    "ENABLE_MODULES": "text2vec-openai,text2vec-cohere,text2vec-huggingface,generative-openai",
                    "CLUSTER_HOSTNAME": "node1",
                }
            ),
            self.service(name, port=8080, target_port=8080),
        ]

        if self.ctx.environment == "local":
            manifests.append(self.node_port_service(name, port=8080, node_port=30080))

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Weaviate health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Weaviate connection string to apps."""
        return {
            "WEAVIATE_URL": f"http://weaviate:{self.port}",
            "WEAVIATE_GRPC_URL": f"weaviate:{self.grpc_port}",
        }


register_module(WeaviateModule)
