"""Keycloak identity and access management module.

Provides SSO, OAuth2/OIDC, social login, and multi-factor authentication.
"""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class KeycloakModule(BaseModule):
    """Keycloak IAM module.

    Manages realms, social login providers, and MFA configuration.
    Depends on PostgreSQL for its backing database.
    """

    NAME = "keycloak"
    CATEGORY = "auth"
    DESCRIPTION = "Keycloak identity and access management (SSO, OAuth2, OIDC)"
    DEFAULT_VERSION = "23.0"
    DEPENDENCIES = ["postgres"]
    CONFLICTS: list[str] = []

    def required_ports(self) -> dict[str, int]:
        """Ports for Keycloak HTTP."""
        return {"keycloak": 8180}

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        realms_data = config.get("keycloak", {}).get("realms", [{"name": "main"}])
        self.realms: list[dict[str, Any]] = realms_data if isinstance(realms_data, list) else [realms_data]

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Keycloak."""
        return {
            "keycloak": {
                "image": f"quay.io/keycloak/keycloak:{self.version}",
                "restart": "unless-stopped",
                "command": "start-dev" if self.ctx.environment == "local" else "start",
                "environment": {
                    "KC_DB": "postgres",
                    "KC_DB_URL": "jdbc:postgresql://postgres:5432/${POSTGRES_DB:-app}",
                    "KC_DB_USERNAME": "${POSTGRES_USER:-postgres}",
                    "KC_DB_PASSWORD": "${POSTGRES_PASSWORD}",
                    "KEYCLOAK_ADMIN": "${KEYCLOAK_ADMIN:-admin}",
                    "KEYCLOAK_ADMIN_PASSWORD": "${KEYCLOAK_ADMIN_PASSWORD}",
                    "KC_HEALTH_ENABLED": "true",
                    "KC_METRICS_ENABLED": "true",
                    "KC_HOSTNAME_STRICT": "false",
                    "KC_PROXY": "edge",
                },
                "ports": [f"{self.ctx.host_port_map.get('keycloak', 8180)}:8080"] if self.ctx.environment == "local" else [],
                "depends_on": {"postgres": {"condition": "service_healthy"}},
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "keycloak",
                    "nikame.category": "auth",
                },
            }
        }

    def health_check(self) -> dict[str, Any]:
        """Keycloak health endpoint."""
        return {
            "test": ["CMD-SHELL", "exec 3<>/dev/tcp/localhost/8080 && echo -e 'GET /health HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n' >&3 && cat <&3 | grep -q 'UP'"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 5,
            "start_period": "60s",
        }

    def env_vars(self) -> dict[str, str]:
        """Auth env vars for other services."""
        return {
            "KEYCLOAK_URL": "http://keycloak:8080",
            "OIDC_ISSUER_URL": "http://keycloak:8080/realms/main",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for Keycloak."""
        return [
            {
                "alert": "KeycloakDown",
                "expr": "up{job='keycloak'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "Keycloak is down"},
            },
            {
                "alert": "KeycloakHighLoginFailures",
                "expr": "rate(keycloak_login_error_total[5m]) > 10",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "High login failure rate on Keycloak"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for Keycloak."""
        return {
            "title": f"{self.ctx.project_name} — Keycloak",
            "uid": "nikame-keycloak",
            "panels": [
                {"title": "Login Success Rate", "type": "stat", "targets": [{"expr": "rate(keycloak_login_total[5m])"}]},
                {"title": "Login Failures", "type": "timeseries", "targets": [{"expr": "rate(keycloak_login_error_total[5m])"}]},
                {"title": "Active Sessions", "type": "gauge", "targets": [{"expr": "keycloak_sessions_count"}]},
                {"title": "JVM Memory", "type": "timeseries", "targets": [{"expr": "jvm_memory_used_bytes{job='keycloak'}"}]},
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cost."""
        return 20.0

    def resource_requirements(self) -> dict[str, Any]:
        """K8s resource requests/limits."""
        return {
            "requests": {"cpu": "500m", "memory": "1Gi"},
            "limits": {"cpu": "1000m", "memory": "2Gi"},
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        # 1. Deployment with Init Container
        deployment: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "keycloak", "namespace": self.ctx.namespace},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "keycloak"}},
                "template": {
                    "metadata": {"labels": {"app": "keycloak"}},
                    "spec": {
                        "serviceAccountName": "keycloak",
                        "initContainers": [
                            self.init_container_wait("postgres", 5432)
                        ],
                        "containers": [
                            {
                                "name": "keycloak",
                                "image": f"quay.io/keycloak/keycloak:{self.version}",
                                "args": ["start"],
                                "ports": [{"containerPort": 8080}],
                                "envFrom": [
                                    {"secretRef": {"name": "keycloak-secret"}},
                                    {"secretRef": {"name": "postgres-secret"}},
                                ],
                                "resources": self.resource_requirements(),
                                "livenessProbe": {
                                    "httpGet": {"path": "/health/live", "port": 8080},
                                    "initialDelaySeconds": 60,
                                },
                                "readinessProbe": {
                                    "httpGet": {"path": "/health/ready", "port": 8080},
                                    "initialDelaySeconds": 30,
                                },
                            }
                        ]
                    },
                },
            },
        }

        # 2. Service
        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "keycloak", "namespace": self.ctx.namespace},
            "spec": {
                "selector": {"app": "keycloak"},
                "ports": [{"port": 8080, "targetPort": 8080}],
            },
        }

        # 3. Production Manifests
        return [
            self.service_account("keycloak"),
            deployment,
            service,
            self.hpa("keycloak", min_reps=1, max_reps=5),
            self.pdb("keycloak"),
        ]
