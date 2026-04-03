"""RabbitMQ messaging module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule


@register_module
class RabbitMQModule(BaseModule):
    """RabbitMQ message broker module."""

    NAME = "rabbitmq"
    CATEGORY = "messaging"
    DESCRIPTION = "RabbitMQ multi-protocol messaging broker"
    DEFAULT_VERSION = "3.12-management"

    def required_ports(self) -> dict[str, int]:
        """Ports for RabbitMQ and Management UI."""
        return {
            "rabbitmq": 5672,
            "rabbitmq-mgmt": 15672,
        }

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for RabbitMQ."""
        return {
            "rabbitmq": {
                "image": f"rabbitmq:{self.version}",
                "restart": "unless-stopped",
                "ports": [
                    f"{self.ctx.host_port_map.get('rabbitmq', 5672)}:5672",
                    f"{self.ctx.host_port_map.get('rabbitmq-mgmt', 15672)}:15672"
                ] if self.ctx.environment == "local" else [],
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
