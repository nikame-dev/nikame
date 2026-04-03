"""Grafana Loki logging module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule


@register_module
class LokiModule(BaseModule):
    """Grafana Loki module."""

    NAME = "loki"
    CATEGORY = "observability"
    DESCRIPTION = "Grafana Loki log aggregation system"
    DEFAULT_VERSION = "2.9.0"

    def required_ports(self) -> dict[str, int]:
        """Standard Loki port."""
        return {"loki": 3100}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Loki."""
        return {
            "loki": {
                "image": f"grafana/loki:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('loki', 3100)}:3100"] if self.ctx.environment == "local" else [],
                "command": ["-config.file=/etc/loki/local-config.yaml"],
                "volumes": [
                    "./configs/loki/local-config.yaml:/etc/loki/local-config.yaml:ro",
                    "loki_data:/loki",
                ],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "loki",
                    "nikame.category": "observability",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment and ConfigMap for Loki."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "loki", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "loki"}},
                    "template": {
                        "metadata": {"labels": {"app": "loki"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "loki",
                                    "image": f"grafana/loki:{self.version}",
                                    "ports": [{"containerPort": 3100}],
                                    "volumeMounts": [{"name": "config", "mountPath": "/etc/loki/local-config.yaml", "subPath": "local-config.yaml"}]
                                }
                            ],
                            "volumes": [{"name": "config", "configMap": {"name": "loki-config"}}]
                        },
                    },
                },
            }
        ]

    def init_scripts(self) -> list[tuple[str, str]]:
        """Default configuration for Loki."""
        config = """
auth_enabled: false
server:
  http_listen_port: 3100
common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
"""
        return [("local-config.yaml", config.strip())]

    def health_check(self) -> dict[str, Any]:
        """Loki health check."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:3100/ready"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
        }

    def env_vars(self) -> dict[str, str]:
        """Expose LOKI_URL."""
        return {"LOKI_URL": "http://loki:3100"}

