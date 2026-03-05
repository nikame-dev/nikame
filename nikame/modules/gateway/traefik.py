"""Traefik reverse proxy and API gateway module.

Cloud-native edge router with automatic TLS via Let's Encrypt,
service discovery via Docker labels, and built-in dashboard.
"""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class TraefikModule(BaseModule):
    """Traefik reverse proxy module.

    Auto-discovers services via Docker labels. Configures TLS
    with Let's Encrypt by default for production deployments.
    """

    NAME = "traefik"
    CATEGORY = "gateway"
    DESCRIPTION = "Traefik reverse proxy with automatic TLS"
    DEFAULT_VERSION = "3.0"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        tls_config = config.get("tls", {})
        self.tls_enabled: bool = tls_config.get("enabled", True)
        self.tls_provider: str = tls_config.get("provider", "letsencrypt")
        self.tls_email: str = tls_config.get("email", "")

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Traefik."""
        command = [
            "--api.dashboard=true",
            "--api.insecure=true" if self.ctx.environment == "local" else "",
            "--providers.docker=true",
            "--providers.docker.exposedbydefault=false",
            "--entrypoints.web.address=:80",
        ]

        ports = ["80:80", "8090:8080"]  # 8090 for dashboard

        if self.tls_enabled and self.ctx.environment != "local":
            command.extend([
                "--entrypoints.websecure.address=:443",
                "--certificatesresolvers.letsencrypt.acme.httpchallenge=true",
                "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web",
                f"--certificatesresolvers.letsencrypt.acme.email={self.tls_email}",
                "--certificatesresolvers.letsencrypt.acme.storage=/acme/acme.json",
            ])
            ports.append("443:443")

        # Filter out empty strings
        command = [c for c in command if c]

        volumes = [
            "/var/run/docker.sock:/var/run/docker.sock:ro",
        ]
        if self.tls_enabled:
            volumes.append("traefik_acme:/acme")

        return {
            "traefik": {
                "image": f"traefik:{self.version}",
                "restart": "unless-stopped",
                "command": command,
                "ports": ports,
                "volumes": volumes,
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "traefik",
                    "nikame.category": "gateway",
                    "traefik.enable": "true",
                    "traefik.http.routers.dashboard.rule": "Host(`dashboard.localhost`) || (Host(`localhost`) && PathPrefix(`/dashboard`))",
                    "traefik.http.routers.dashboard.service": "api@internal",
                },
            }
        }


    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s Deployment + Service + IngressClass for Traefik."""
        deployment: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "traefik", "namespace": self.ctx.namespace},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "traefik"}},
                "template": {
                    "metadata": {"labels": {"app": "traefik"}},
                    "spec": {
                        "serviceAccountName": "traefik",
                        "containers": [
                            {
                                "name": "traefik",
                                "image": f"traefik:{self.version}",
                                "args": [
                                    "--providers.kubernetescrd",
                                    "--entrypoints.web.address=:80",
                                    "--entrypoints.websecure.address=:443",
                                    "--api.dashboard=true",
                                ],
                                "ports": [
                                    {"containerPort": 80, "name": "web"},
                                    {"containerPort": 443, "name": "websecure"},
                                    {"containerPort": 8080, "name": "dashboard"},
                                ],
                                "resources": self.resource_requirements(),
                            }
                        ],
                    },
                },
            },
        }

        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "traefik", "namespace": self.ctx.namespace},
            "spec": {
                "type": "LoadBalancer",
                "selector": {"app": "traefik"},
                "ports": [
                    {"port": 80, "targetPort": 80, "name": "web"},
                    {"port": 443, "targetPort": 443, "name": "websecure"},
                ],
            },
        }

        # 3. Production Manifests
        return [
            deployment,
            service,
            self.hpa("traefik", min_reps=2, max_reps=5),
            self.pdb("traefik"),
        ]

    def health_check(self) -> dict[str, Any]:
        """Traefik API health check."""
        return {
            "test": ["CMD", "traefik", "healthcheck"],
            "interval": "15s",
            "timeout": "5s",
            "retries": 3,
            "start_period": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Gateway env vars."""
        scheme = "https" if self.tls_enabled else "http"
        domain = self.ctx.domain or "localhost"
        return {
            "GATEWAY_URL": f"{scheme}://{domain}",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for Traefik."""
        return [
            {
                "alert": "TraefikDown",
                "expr": "up{job='traefik'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "Traefik is down"},
            },
            {
                "alert": "TraefikHighErrorRate",
                "expr": 'rate(traefik_entrypoint_requests_total{code=~"5.."}[5m]) / rate(traefik_entrypoint_requests_total[5m]) > 0.05',
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Traefik error rate above 5%"},
            },
            {
                "alert": "TraefikTLSCertExpiring",
                "expr": "(traefik_tls_certs_not_after - time()) / 86400 < 14",
                "for": "1h",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Traefik TLS certificate expiring in <14 days"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for Traefik."""
        return {
            "title": f"{self.ctx.project_name} — Traefik",
            "uid": "nikame-traefik",
            "panels": [
                {"title": "Requests/sec", "type": "timeseries", "targets": [{"expr": "rate(traefik_entrypoint_requests_total[5m])"}]},
                {"title": "Error Rate", "type": "stat", "targets": [{"expr": 'rate(traefik_entrypoint_requests_total{code=~"5.."}[5m])'}]},
                {"title": "Average Latency", "type": "timeseries", "targets": [{"expr": "rate(traefik_entrypoint_request_duration_seconds_sum[5m]) / rate(traefik_entrypoint_request_duration_seconds_count[5m])"}]},
                {"title": "Active Connections", "type": "gauge", "targets": [{"expr": "traefik_entrypoint_open_connections"}]},
            ],
        }

    def prometheus_scrape_targets(self) -> list[dict[str, Any]]:
        """Return Prometheus scrape configurations for Traefik."""
        return [
            {
                "job_name": "traefik",
                "static_configs": [{"targets": ["traefik:8080"]}],
            }
        ]

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate — Traefik itself is free, just compute cost."""
        return 10.0
