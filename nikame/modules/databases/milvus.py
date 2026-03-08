"""Milvus vector database module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class MilvusModule(BaseModule):
    """Milvus vector database module.

    Configures a standalone Milvus instance for semantic search.
    Requires MinIO and etcd (or embedded equivalents depending on version).
    """

    NAME = "milvus"
    CATEGORY = "database"
    DESCRIPTION = "Milvus vector database"
    DEFAULT_VERSION = "v2.3.15"
    DEFAULT_PORT = 19530
    # True standalone now often requires etcd/minio as separate containers or embedded
    # Using the standard milvus standalone image for simplicity here

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Milvus port."""
        return {
            "milvus": self.port,
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Milvus."""
        project = self.ctx.project_name
        return {
            "milvus": {
                "image": f"milvusdb/milvus:{self.version}",
                "command": ["milvus", "run", "standalone"],
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('milvus', self.port)}:19530"
                ] if self.ctx.environment == "local" else [],
                "environment": {
                    "ETCD_USE_EMBED": "true",
                    "ETCD_DATA_DIR": "/var/lib/milvus/etcd",
                    "ETCD_CONFIG_PATH": "/milvus/configs/embedEtcd.yaml",
                    "COMMON_STORAGETYPE": "local",
                },
                "volumes": ["milvus_data:/var/lib/milvus"],
                "healthcheck": self.health_check(),
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "labels": {
                    "nikame.module": "milvus",
                    "nikame.category": "database",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Milvus."""
        name = "milvus"
        image = f"milvusdb/milvus:{self.version}"

        manifests = [
            self.service_account(name),
            self.stateful_set(
                name=name,
                image=image,
                port=19530,
                pvc_name=f"{name}-data",
                pvc_size="20Gi",
                env_from=[{"configMapRef": {"name": f"{name}-config"}}],
                liveness_probe=self.health_check(),
            ),
            self.config_map(
                name=f"{name}-config",
                data={
                    "ETCD_USE_EMBED": "true",
                    "ETCD_DATA_DIR": "/var/lib/milvus/etcd",
                    "ETCD_CONFIG_PATH": "/milvus/configs/embedEtcd.yaml",
                    "COMMON_STORAGETYPE": "local",
                }
            ),
            self.service(name, port=19530, target_port=19530),
        ]

        if self.ctx.environment == "local":
            manifests.append(self.node_port_service(name, port=19530, node_port=30530))

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Milvus health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:9091/healthz"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Milvus connection string to apps."""
        return {
            "MILVUS_URI": f"http://milvus:{self.port}",
        }


register_module(MilvusModule)
