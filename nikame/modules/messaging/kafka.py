"""Apache Kafka messaging module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class KafkaModule(BaseModule):
    """Apache Kafka module with KRaft mode."""

    NAME = "kafka"
    CATEGORY = "messaging"
    DESCRIPTION = "Apache Kafka distributed event streaming platform"
    DEFAULT_VERSION = "3.7"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = ["redpanda"]

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Kafka (KRaft)."""
        return {
            "kafka": {
                "image": f"confluentinc/cp-kafka:{self.version}",
                "restart": "unless-stopped",
                "ports": ["9092:9092"],
                "environment": {
                    "KAFKA_NODE_ID": "1",
                    "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT",
                    "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092",
                    "KAFKA_PROCESS_ROLES": "broker,controller",
                    "KAFKA_CONTROLLER_QUORUM_VOTERS": "1@kafka:29093",
                    "KAFKA_LISTENERS": "PLAINTEXT://kafka:29092,CONTROLLER://kafka:29093,PLAINTEXT_HOST://0.0.0.0:9092",
                    "KAFKA_INTER_BROKER_LISTENER_NAME": "PLAINTEXT",
                    "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
                    "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
                },
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Kafka."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "kafka", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "kafka"}},
                    "template": {
                        "metadata": {"labels": {"app": "kafka"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "kafka",
                                    "image": f"confluentinc/cp-kafka:{self.version}",
                                    "ports": [{"containerPort": 9092}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Kafka health check."""
        return {
            "test": ["CMD", "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose KAFKA_BOOTSTRAP_SERVERS."""
        return {
            "KAFKA_BOOTSTRAP_SERVERS": "kafka:29092",
        }
