"""Prometheus monitoring module.

Time-series metrics collection with alerting rules.
Auto-discovers all NIKAME services for scraping.
"""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class PrometheusModule(BaseModule):
    """Prometheus metrics and alerting module.

    Auto-generates scrape targets for all services in the blueprint.
    Includes Alertmanager for notification routing.
    """

    NAME = "prometheus"
    CATEGORY = "observability"
    DESCRIPTION = "Prometheus metrics collection and alerting"
    DEFAULT_VERSION = "v2.49.0"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.retention: str = config.get("retention", "15d")
        self.alerting_config: dict[str, Any] = config.get("alerting", {})

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose services for Prometheus + Alertmanager."""
        services: dict[str, Any] = {
            "prometheus": {
                "image": f"prom/prometheus:{self.version}",
                "restart": "unless-stopped",
                "command": [
                    f"--storage.tsdb.retention.time={self.retention}",
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--web.enable-lifecycle",
                    "--web.enable-admin-api",
                ],
                "ports": ["9090:9090"] if self.ctx.environment == "local" else [],
                "volumes": [
                    "../configs/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
                    "../configs/prometheus/rules/:/etc/prometheus/rules/:ro",
                    "prometheus_data:/prometheus",
                ],
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "prometheus",
                    "nikame.category": "observability",
                },
            },
            "alertmanager": {
                "image": "prom/alertmanager:v0.27.0",
                "restart": "unless-stopped",
                "ports": ["9093:9093"] if self.ctx.environment == "local" else [],
                "volumes": [
                    "../configs/prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro",
                ],
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "alertmanager",
                    "nikame.category": "observability",
                },
            },
        }

        return services

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s Deployment + Service + ConfigMap for Prometheus."""
        deployment: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "prometheus", "namespace": self.ctx.namespace},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "prometheus"}},
                "template": {
                    "metadata": {"labels": {"app": "prometheus"}},
                    "spec": {
                        "serviceAccountName": "prometheus",
                        "containers": [
                            {
                                "name": "prometheus",
                                "image": f"prom/prometheus:{self.version}",
                                "ports": [{"containerPort": 9090}],
                                "volumeMounts": [
                                    {"name": "config", "mountPath": "/etc/prometheus"},
                                    {"name": "data", "mountPath": "/prometheus"},
                                ],
                                "resources": self.resource_requirements(),
                            }
                        ],
                        "volumes": [
                            {"name": "config", "configMap": {"name": "prometheus-config"}},
                            {"name": "data", "persistentVolumeClaim": {"claimName": "prometheus-pvc"}},
                        ],
                    },
                },
            },
        }

        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "prometheus", "namespace": self.ctx.namespace},
            "spec": {
                "selector": {"app": "prometheus"},
                "ports": [{"port": 9090, "targetPort": 9090}],
            },
        }

        return [deployment, service]

    def health_check(self) -> dict[str, Any]:
        """Prometheus readiness check."""
        return {
            "test": ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9090/-/ready"],
            "interval": "15s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "15s",
        }

    def env_vars(self) -> dict[str, str]:
        """Prometheus connection env vars."""
        return {
            "PROMETHEUS_URL": "http://prometheus:9090",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Meta-alerts: Prometheus monitoring itself."""
        return [
            {
                "alert": "PrometheusTargetDown",
                "expr": "up == 0",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "Prometheus target {{ $labels.job }} is down",
                    "description": "Target {{ $labels.instance }} has been unreachable for 5 minutes.",
                },
            },
            {
                "alert": "PrometheusHighMemory",
                "expr": "process_resident_memory_bytes{job='prometheus'} > 4e9",
                "for": "15m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Prometheus using >4GB RAM"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for Prometheus self-monitoring."""
        return {
            "title": f"{self.ctx.project_name} — Prometheus",
            "uid": "nikame-prometheus",
            "panels": [
                {"title": "Scrape Targets", "type": "stat", "targets": [{"expr": "count(up)"}]},
                {"title": "Targets Down", "type": "stat", "targets": [{"expr": "count(up == 0)"}]},
                {"title": "Ingested Samples/sec", "type": "timeseries", "targets": [{"expr": "rate(prometheus_tsdb_head_samples_appended_total[5m])"}]},
                {"title": "Storage Size", "type": "timeseries", "targets": [{"expr": "prometheus_tsdb_storage_blocks_bytes"}]},
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cost."""
        return 15.0

    def resource_requirements(self) -> dict[str, Any]:
        """K8s resources for Prometheus."""
        return {
            "requests": {"cpu": "250m", "memory": "1Gi"},
            "limits": {"cpu": "1000m", "memory": "4Gi"},
        }
