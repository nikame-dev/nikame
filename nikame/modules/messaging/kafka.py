"""Apache Kafka messaging module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any
import json

from nikame.modules.base import BaseModule


@register_module
class KafkaModule(BaseModule):
    """Apache Kafka module with KRaft mode."""

    NAME = "kafka"
    CATEGORY = "messaging"
    DESCRIPTION = "Apache Kafka distributed event streaming platform"
    DEFAULT_VERSION = "3.7"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = ["redpanda"]

    def required_ports(self) -> dict[str, int]:
        """Standard Kafka port."""
        return {"kafka": 9092}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Kafka (KRaft)."""
        return {
            "kafka": {
                "image": f"confluentinc/cp-kafka:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('kafka', 9092)}:9092"] if self.ctx.environment == "local" else [],
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

    def scaffold_files(self) -> list[tuple[str, str]]:
        """Generate producer and worker templates for Kafka."""
        files: list[tuple[str, str]] = []

        producer_py = '''"""
Kafka message producer.
"""

import json
from aiokafka import AIOKafkaProducer
from config import settings

async def get_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    await producer.start()
    return producer

async def send_message(topic: str, message: dict):
    producer = await get_producer()
    try:
        await producer.send_and_wait(topic, message)
    finally:
        await producer.stop()
'''

        worker_py = '''"""
Kafka message worker.
"""

import asyncio
import json
from aiokafka import AIOKafkaConsumer
from config import settings

async def start_worker(topic: str, group_id: str):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print(f"Consumed message: {msg.value} from {msg.topic}")
            # Handle message logic here
    finally:
        await consumer.stop()

if __name__ == "__main__":
    # Example usage: python worker.py
    asyncio.run(start_worker("events", "nikame-workers"))
'''
        files.append(("app/core/messaging/__init__.py", ""))
        files.append(("app/core/messaging/producer.py", producer_py))
        files.append(("app/core/messaging/worker.py", worker_py))
        return files
