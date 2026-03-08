"""MLflow experiment tracking module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class MLflowModule(BaseModule):
    """MLflow module for experiment tracking.

    Configures MLflow server with:
    - Postgres backend for metadata tracking
    - MinIO (S3) for artifact storage
    """

    NAME = "mlflow"
    CATEGORY = "ml"
    DESCRIPTION = "MLflow experiment tracking and model registry"
    DEFAULT_VERSION = "2.10.2"
    DEFAULT_PORT = 5000
    DEPENDENCIES = ["postgres", "minio"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested MLflow port."""
        return {"mlflow": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for MLflow."""
        project = self.ctx.project_name
        return {
            "mlflow": {
                "image": f"ghcr.io/mlflow/mlflow:v{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('mlflow', self.port)}:5000"],
                "environment": {
                    "MLFLOW_S3_ENDPOINT_URL": "http://minio:9000",
                    "AWS_ACCESS_KEY_ID": "${MINIO_ROOT_USER:-minioadmin}",
                    "AWS_SECRET_ACCESS_KEY": "${MINIO_ROOT_PASSWORD}",
                    "MLFLOW_S3_IGNORE_TLS": "true",
                },
                "command": [
                    "mlflow", "server",
                    "--host", "0.0.0.0",
                    "--port", "5000",
                    "--backend-store-uri", "postgresql://user:password@postgres:5432/mlflow",
                    "--default-artifact-root", "s3://mlflow",
                ],
                "depends_on": {
                    "postgres": {"condition": "service_healthy"},
                    "minio": {"condition": "service_healthy"},
                },
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "labels": {
                    "nikame.module": "mlflow",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for MLflow."""
        name = "mlflow"
        image = f"ghcr.io/mlflow/mlflow:v{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=5000,
                env={
                    "MLFLOW_S3_ENDPOINT_URL": "http://minio:9000",
                    "MLFLOW_S3_IGNORE_TLS": "true",
                },
                command=[
                    "mlflow", "server",
                    "--host", "0.0.0.0",
                    "--port", "5000",
                    "--backend-store-uri", "$(DATABASE_URL)",
                    "--default-artifact-root", "s3://mlflow",
                ]
            ),
            self.service(name, port=5000, target_port=5000),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"mlflow.{self.ctx.domain}", service_port=5000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """MLflow health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:5000/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose tracking URI."""
        return {
            "MLFLOW_TRACKING_URI": f"http://mlflow:{self.port}",
            "MLFLOW_S3_ENDPOINT_URL": "http://minio:9000",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for MLflow."""
        return [
            {
                "alert": "MLflowDown",
                "expr": "up{job='mlflow'} == 0",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "MLflow tracking server is unreachable"},
            }
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Simple dashboard for MLflow."""
        return {
            "title": f"{self.ctx.project_name} — MLflow",
            "uid": "nikame-mlflow",
            "panels": [
                {"title": "Server Status", "type": "stat", "targets": [{"expr": "up{job='mlflow'}"}]},
            ],
        }


register_module(MLflowModule)
