"""Evidently AI module for ML Monitoring."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class EvidentlyModule(BaseModule):
    """Evidently AI module for data drift and ML model monitoring.

    Configures the Evidently UI server for viewing dashboards.
    """

    NAME = "evidently"
    CATEGORY = "ml"
    DESCRIPTION = "Evidently AI monitoring and drift detection"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 8085

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Evidently port."""
        return {"evidently": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Evidently."""
        project = self.ctx.project_name
        return {
            "evidently": {
                "image": "python:3.11-slim",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('evidently', self.port)}:8000"],
                "command": "bash -c 'pip install evidently && evidently ui --port 8000 --host 0.0.0.0 --workspace /app/workspace'",
                "volumes": ["evidently_data:/app/workspace"],
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "evidently",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Evidently."""
        name = "evidently"
        image = "python:3.11-slim"

        # Using a custom command for the simple python image
        deployment = self.deployment(
            name=name,
            image=image,
            port=8000,
            command=["bash", "-c", "pip install evidently && evidently ui --port 8000 --host 0.0.0.0 --workspace /app/workspace"]
        )
        
        # Add PVC mount manually as the base `deployment` helper doesn't attach volumes by default
        pvc_name = f"{name}-data"
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        container["volumeMounts"] = [{"name": "data", "mountPath": "/app/workspace"}]
        deployment["spec"]["template"]["spec"]["volumes"] = [
            {"name": "data", "persistentVolumeClaim": {"claimName": pvc_name}}
        ]

        manifests = [
            self.service_account(name),
            self.pvc(pvc_name, size="5Gi"),
            deployment,
            self.service(name, port=8000, target_port=8000),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"evidently.{self.ctx.domain}", service_port=8000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Evidently health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 5,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Evidently Host URL to apps if needed."""
        return {
            "EVIDENTLY_HOST": f"http://evidently:{self.port}",
        }


register_module(EvidentlyModule)
