"""Grafana Tempo tracing module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class TempoModule(BaseModule):
    """Grafana Tempo tracing module."""

    NAME = "tempo"
    CATEGORY = "observability"
    DESCRIPTION = "Grafana Tempo high-scale distributed tracing backend"
    DEFAULT_VERSION = "2.3.0"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Tempo."""
        return {
            "tempo": {
                "image": f"grafana/tempo:{self.version}",
                "restart": "unless-stopped",
                "ports": ["3200:3200"],
                "command": ["-config.file=/etc/tempo.yaml"],
                "volumes": [
                    "./configs/tempo/tempo.yaml:/etc/tempo.yaml:ro",
                    "tempo_data:/var/tempo",
                ],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "tempo",
                    "nikame.category": "observability",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment and ConfigMap for Tempo."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "tempo", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "tempo"}},
                    "template": {
                        "metadata": {"labels": {"app": "tempo"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "tempo",
                                    "image": f"grafana/tempo:{self.version}",
                                    "ports": [{"containerPort": 3200}],
                                    "volumeMounts": [{"name": "config", "mountPath": "/etc/tempo.yaml", "subPath": "tempo.yaml"}]
                                }
                            ],
                            "volumes": [{"name": "config", "configMap": {"name": "tempo-config"}}]
                        },
                    },
                },
            }
        ]

    def init_scripts(self) -> list[tuple[str, str]]:
        """Default configuration for Tempo."""
        config = """
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
        http:

ingester:
  max_block_duration: 5m

compactor:
  compaction:
    compaction_cycle: 1m
    block_retention: 1h

storage:
  trace:
    backend: local
    local:
      path: /var/tempo-data
    wal:
      path: /var/tempo-data/wal
"""
        return [("tempo.yaml", config.strip())]

    def health_check(self) -> dict[str, Any]:
        """Tempo health check."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:3200/ready"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose TEMPO_URL."""
        return {"TEMPO_URL": "http://tempo:3200", "OTLP_ENDPOINT": "http://tempo:4317"}

