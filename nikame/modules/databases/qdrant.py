"""Qdrant vector database module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class QdrantModule(BaseModule):
    """Qdrant vector similarity search engine module."""

    NAME = "qdrant"
    CATEGORY = "database"
    DESCRIPTION = "Qdrant vector database for AI/ML"
    DEFAULT_VERSION = "latest"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Qdrant."""
        return {
            "qdrant": {
                "image": f"qdrant/qdrant:{self.version}",
                "restart": "unless-stopped",
                "ports": ["6333:6333", "6334:6334"],
                "volumes": ["qdrant_data:/qdrant/storage"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate full production-ready K8s architecture for Qdrant."""
        name = "qdrant"
        image = f"qdrant/qdrant:{self.version}"

        # 1. StatefulSet
        ss = self.stateful_set(
            name=name,
            image=image,
            port=6333,
            pvc_name=f"{name}-data",
            pvc_size="10Gi",
            liveness_probe={"httpGet": {"path": "/healthz", "port": 6333}, "initialDelaySeconds": 15}
        )
        # Add gRPC port
        ss["spec"]["template"]["spec"]["containers"][0]["ports"].append({"containerPort": 6334, "name": "grpc"})

        # 2. Service
        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name, "namespace": self.ctx.namespace, "labels": {"app": name}},
            "spec": {
                "selector": {"app": name},
                "ports": [
                    {"port": 6333, "targetPort": 6333, "name": "http"},
                    {"port": 6334, "targetPort": 6334, "name": "grpc"},
                ],
            },
        }

        # 3. Production Manifests
        manifests = [
            self.service_account(name),
            ss,
            service,
            self.network_policy(name, allow_from=["api", "worker"]),
            self.hpa(name, min_reps=1, max_reps=3),
            self.pdb(name, min_available=1),
        ]

        if self.ctx.domain:
            manifests.append(self.ingress(name, f"qdrant.{self.ctx.domain}", service_port=6333, tls_secret=f"{name}-tls"))

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Qdrant health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:6333/healthz"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose QDRANT_URL."""
        return {"QDRANT_URL": "http://qdrant:6333"}
