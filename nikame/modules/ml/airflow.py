"""Airflow orchestration module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class AirflowModule(BaseModule):
    """Apache Airflow orchestrator module.

    Configures a lightweight Airflow standalone/LocalExecutor setup.
    """

    NAME = "airflow"
    CATEGORY = "ml"
    DESCRIPTION = "Apache Airflow pipeline orchestration"
    DEFAULT_VERSION = "2.8.1"
    DEFAULT_PORT = 8080
    DEPENDENCIES = ["postgres"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)

    def required_ports(self) -> dict[str, int]:
        """Requested Airflow port."""
        return {"airflow": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Airflow."""
        project = self.ctx.project_name
        return {
            "airflow": {
                "image": f"apache/airflow:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('airflow', self.port)}:8080"],
                "environment": {
                    "AIRFLOW__CORE__EXECUTOR": "LocalExecutor",
                    "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN": "postgresql+psycopg2://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@postgres:5432/airflow",
                    "AIRFLOW__CORE__FERNET_KEY": "airflow-fernet-key-placeholder",
                    "AIRFLOW__CORE__LOAD_EXAMPLES": "false",
                    "AIRFLOW__API__AUTH_BACKENDS": "airflow.api.auth.backend.basic_auth",
                },
                "command": "standalone",
                "depends_on": {
                    "postgres": {"condition": "service_healthy"},
                },
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "airflow",
                    "nikame.category": "ml",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for Airflow."""
        name = "airflow"
        image = f"apache/airflow:{self.version}"

        manifests = [
            self.service_account(name),
            self.deployment(
                name=name,
                image=image,
                port=8080,
                command=["airflow", "standalone"],
                env={
                    "AIRFLOW__CORE__EXECUTOR": "LocalExecutor",
                    "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN": "$(DATABASE_URL)",
                    "AIRFLOW__CORE__FERNET_KEY": "airflow-fernet-key-placeholder",
                    "AIRFLOW__CORE__LOAD_EXAMPLES": "false",
                }
            ),
            self.service(name, port=8080, target_port=8080),
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"airflow.{self.ctx.domain}", service_port=8080)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Airflow server health check."""
        return {
            "test": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 5,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose Airflow Webserver URL."""
        return {
            "AIRFLOW_API_URL": f"http://airflow:{self.port}",
        }


