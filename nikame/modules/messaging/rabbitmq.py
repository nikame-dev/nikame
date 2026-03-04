"""RabbitMQ messaging module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class RabbitMQModule(BaseModule):
    """RabbitMQ message broker module."""

    NAME = "rabbitmq"
    CATEGORY = "messaging"
    DESCRIPTION = "RabbitMQ multi-protocol messaging broker"
    DEFAULT_VERSION = "3.12-management"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for RabbitMQ."""
        return {
            "rabbitmq": {
                "image": f"rabbitmq:{self.version}",
                "restart": "unless-stopped",
                "ports": ["5672:5672", "15672:15672"],
                "environment": {
                    "RABBITMQ_DEFAULT_USER": "guest",
                    "RABBITMQ_DEFAULT_PASS": "guest",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for RabbitMQ."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {"name": "rabbitmq", "namespace": self.ctx.namespace},
                "spec": {
                    "serviceName": "rabbitmq",
                    "replicas": 1,
                    "selector": {"matchLabels": {"app": "rabbitmq"}},
                    "template": {
                        "metadata": {"labels": {"app": "rabbitmq"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "rabbitmq",
                                    "image": f"rabbitmq:{self.version}",
                                    "ports": [{"containerPort": 5672}, {"containerPort": 15672}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """RabbitMQ health check."""
        return {
            "test": ["CMD", "rabbitmq-diagnostics", "-q", "ping"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose RABBITMQ_URL."""
        return {"RABBITMQ_URL": "amqp://guest:guest@rabbitmq:5672"}
