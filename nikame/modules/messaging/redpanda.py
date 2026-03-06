"""RedPanda streaming platform module.

RedPanda is NIKAME's recommended alternative to Apache Kafka — no JVM,
10x faster startup, fully Kafka-compatible API, built-in Schema
Registry and Console UI.
"""

from __future__ import annotations

from typing import Any
import json

from nikame.modules.base import BaseModule, ModuleContext


class RedPandaModule(BaseModule):
    """RedPanda streaming platform module.

    Kafka-compatible streaming with no JVM overhead. Includes
    optional Schema Registry and RedPanda Console UI.
    """

    NAME = "redpanda"
    CATEGORY = "messaging"
    DESCRIPTION = "RedPanda — Kafka-compatible streaming with no JVM, 10x faster"
    DEFAULT_VERSION = "latest"
    DEPENDENCIES: list[str] = []
    CONFLICTS = ["kafka"]

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.brokers: int = config.get("brokers", 1)
        self.topics: list[dict[str, Any]] = config.get("topics", [])
        self.schema_registry: bool = config.get("schema_registry", True)
        self.kafka_ui: bool = config.get("kafka_ui", True)

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose services for RedPanda + Console."""
        services: dict[str, Any] = {
            "redpanda": {
                "image": f"redpandadata/redpanda:{self.version}",
                "restart": "unless-stopped",
                "command": [
                    "redpanda", "start",
                    "--smp", "1",
                    "--memory", "1G",
                    "--reserve-memory", "0M",
                    "--overprovisioned",
                    "--kafka-addr", "internal://0.0.0.0:9092,external://0.0.0.0:19092",
                    "--advertise-kafka-addr", "internal://redpanda:9092,external://localhost:19092",
                    "--schema-registry-addr", "internal://0.0.0.0:8081,external://0.0.0.0:18081",
                ],
                "ports": (
                    [
                        f"{self.ctx.host_port_map.get('redpanda', 19092)}:19092",
                        "18081:18081",
                        "9644:9644"
                    ]
                    if self.ctx.environment == "local"
                    else []
                ),
                "volumes": ["redpanda_data:/var/lib/redpanda/data"],
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "redpanda",
                    "nikame.category": "messaging",
                },
            }
        }

        if self.kafka_ui:
            services["redpanda-console"] = {
                "image": "redpandadata/console:v2.4.3",
                "restart": "unless-stopped",
                "environment": {
                    "KAFKA_BROKERS": "redpanda:9092",
                    "SCHEMA_REGISTRY_URL": "http://redpanda:8081",
                },
                "ports": [f"{self.ctx.host_port_map.get('redpanda-console', 8080)}:8080"] if self.ctx.environment == "local" else [],
                "depends_on": {"redpanda": {"condition": "service_healthy"}},
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "redpanda-console",
                    "nikame.category": "messaging",
                },
            }

        return services

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s StatefulSet + Service for RedPanda."""
        statefulset: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {
                "name": "redpanda",
                "namespace": self.ctx.namespace,
            },
            "spec": {
                "serviceName": "redpanda",
                "replicas": self.brokers,
                "selector": {"matchLabels": {"app": "redpanda"}},
                "template": {
                    "metadata": {"labels": {"app": "redpanda"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "redpanda",
                                "image": f"redpandadata/redpanda:{self.version}",
                                "ports": [
                                    {"containerPort": 9092, "name": "kafka"},
                                    {"containerPort": 8081, "name": "schema-registry"},
                                    {"containerPort": 9644, "name": "admin"},
                                ],
                                "resources": self.resource_requirements(),
                            }
                        ]
                    },
                },
            },
        }

        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "redpanda", "namespace": self.ctx.namespace},
            "spec": {
                "selector": {"app": "redpanda"},
                "ports": [
                    {"port": 9092, "targetPort": 9092, "name": "kafka"},
                    {"port": 8081, "targetPort": 8081, "name": "schema-registry"},
                ],
                "clusterIP": "None",
            },
        }

        return [statefulset, service]

    def health_check(self) -> dict[str, Any]:
        """RedPanda admin API health check."""
        return {
            "test": ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy.*true'|| exit 1"],
            "interval": "15s",
            "timeout": "10s",
            "retries": 5,
            "start_period": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Kafka-compatible connection env vars."""
        return {
            "KAFKA_BOOTSTRAP_SERVERS": "redpanda:9092",
            "SCHEMA_REGISTRY_URL": "http://redpanda:8081",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for RedPanda."""
        return [
            {
                "alert": "RedPandaDown",
                "expr": "up{job='redpanda'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "RedPanda broker is down"},
            },
            {
                "alert": "RedPandaUnderReplicatedPartitions",
                "expr": "redpanda_kafka_under_replicated_replicas > 0",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "RedPanda has under-replicated partitions"},
            },
            {
                "alert": "RedPandaHighLatency",
                "expr": "redpanda_kafka_request_latency_seconds{quantile='0.99'} > 1",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "RedPanda p99 latency above 1 second"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for RedPanda."""
        return {
            "title": f"{self.ctx.project_name} — RedPanda",
            "uid": "nikame-redpanda",
            "panels": [
                {"title": "Messages In/sec", "type": "timeseries", "targets": [{"expr": "rate(redpanda_kafka_request_bytes_total[5m])"}]},
                {"title": "Consumer Lag", "type": "timeseries", "targets": [{"expr": "redpanda_kafka_consumer_group_lag"}]},
                {"title": "Partition Count", "type": "stat", "targets": [{"expr": "redpanda_kafka_partitions"}]},
                {"title": "Broker Disk Usage", "type": "gauge", "targets": [{"expr": "redpanda_storage_disk_used_bytes"}]},
            ],
        }

    def prometheus_scrape_targets(self) -> list[dict[str, Any]]:
        """Return Prometheus scrape configurations for RedPanda."""
        return [
            {
                "job_name": "redpanda",
                "static_configs": [{"targets": ["redpanda:9644"]}],
            }
        ]

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cost."""
        return 30.0 * self.brokers

    def resource_requirements(self) -> dict[str, Any]:
        """K8s resource requests/limits for RedPanda."""
        return {
            "requests": {"cpu": "500m", "memory": "1Gi"},
            "limits": {"cpu": "2000m", "memory": "2Gi"},
        }

    def scaffold_files(self) -> list[tuple[str, str]]:
        """Generate producer and worker templates for RedPanda."""
        files: list[tuple[str, str]] = []

        producer_py = '''"""
RedPanda/Kafka message producer.
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
RedPanda/Kafka message worker.
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
