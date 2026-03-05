"""OpenTelemetry Collector module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule


class OTELCollectorModule(BaseModule):
    """OpenTelemetry Collector module."""

    NAME = "otel_collector"
    CATEGORY = "observability"
    DESCRIPTION = "OpenTelemetry Collector for vendor-agnostic telemetry ingestion"
    DEFAULT_VERSION = "0.96.0"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for OTEL Collector."""
        return {
            "otel-collector": {
                "image": f"otel/opentelemetry-collector-contrib:{self.version}",
                "restart": "unless-stopped",
                "ports": ["4317:4317", "4318:4318", "8888:8888", "8889:8889", "13133:13133"],
                "command": ["--config=/etc/otel-collector-config.yaml"],
                "volumes": [
                    "./configs/otel_collector/otel-collector-config.yaml:/etc/otel-collector-config.yaml:ro"
                ],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "otel_collector",
                    "nikame.category": "observability",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment and ConfigMap for OTEL Collector."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "otel-collector", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "otel-collector"}},
                    "template": {
                        "metadata": {"labels": {"app": "otel-collector"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "otel-collector",
                                    "image": f"otel/opentelemetry-collector-contrib:{self.version}",
                                    "ports": [{"containerPort": 4317}],
                                    "volumeMounts": [{"name": "config", "mountPath": "/etc/otel-collector-config.yaml", "subPath": "otel-collector-config.yaml"}]
                                }
                            ],
                            "volumes": [{"name": "config", "configMap": {"name": "otel-collector-config"}}]
                        },
                    },
                },
            }
        ]

    def init_scripts(self) -> list[tuple[str, str]]:
        """Default configuration for OTEL Collector."""
        config = """
receivers:
  otlp:
    protocols:
      grpc:
      http:
  prometheus:
    config:
      scrape_configs:
        - job_name: 'otel-collector'
          scrape_interval: 5s
          static_configs:
            - targets: ['0.0.0.0:8888']

exporters:
  logging:
    verbosity: normal
  prometheus:
    endpoint: "0.0.0.0:8889"

extensions:
  health_check:

service:
  extensions: [health_check]
  pipelines:
    metrics:
      receivers: [otlp, prometheus]
      exporters: [logging, prometheus]
    traces:
      receivers: [otlp]
      exporters: [logging]
"""
        return [("otel-collector-config.yaml", config.strip())]

    def health_check(self) -> dict[str, Any]:
        """OTEL health check extension."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:13133/health"],
            "interval": "15s",
            "timeout": "5s",
            "retries": 3,
        }

    def prometheus_scrape_targets(self) -> list[dict[str, Any]]:
        """Return Prometheus scrape configurations for OTEL Collector."""
        return [
            {
                "job_name": "otel-collector",
                "static_configs": [{"targets": ["otel-collector:8889"]}],
            }
        ]

    def env_vars(self) -> dict[str, str]:
        """Expose OTEL_COLLECTOR_URL."""
        return {"OTEL_COLLECTOR_URL": "http://otel-collector:4317"}

