"""OpenTelemetry Collector module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


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
                "ports": ["4317:4317", "4318:4318", "8888:8888", "8889:8889"],
                "command": "--config=/etc/otel-collector-config.yaml",
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for OTEL Collector."""
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
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """OTEL health check."""
        return {
            "test": ["CMD", "wget", "-qO-", "http://localhost:13133/health"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose OTEL_COLLECTOR_URL."""
        return {"OTEL_COLLECTOR_URL": "http://otel-collector:4317"}
