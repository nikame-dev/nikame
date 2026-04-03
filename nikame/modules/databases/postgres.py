"""PostgreSQL relational database module.

Supports single instance, streaming replication, pgBouncer connection
pooling, and common extensions (pgvector, TimescaleDB, PostGIS, etc.).
"""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class PostgresModule(BaseModule):
    """PostgreSQL database module with optional pgBouncer pooling.

    Auto-enables pgBouncer by default (NIKAME smart default).
    Generates init scripts for requested extensions.
    """

    NAME = "postgres"
    CATEGORY = "database"
    DESCRIPTION = "PostgreSQL relational database with optional replication and pooling"
    DEFAULT_VERSION = "16"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.max_connections: int = config.get("max_connections", 100)
        self.replicas: int = config.get("replicas", 1)
        self.pgbouncer: bool = config.get("pgbouncer", True)
        self.storage: str = config.get("storage", "10Gi")
        self.extensions: list[str] = config.get("extensions", [])
        
        self.is_pgvector = "pgvector" in self.ctx.active_modules
        if self.is_pgvector and "vector" not in self.extensions:
            self.extensions.append("vector")


    def required_ports(self) -> dict[str, int]:
        """Standard PostgreSQL port."""
        return {"postgres": 5432}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose services for PostgreSQL + pgBouncer.
        
        If replicas > 1, switches to Bitnami images for automated replication setup.
        """
        project = self.ctx.project_name
        
        # Single instance case: Stick to official alpine image for simplicity
        if self.replicas == 1:
            raw_image = f"pgvector/pgvector:pg{self.version}" if getattr(self, "is_pgvector", False) else f"postgres:{self.version}-alpine"
            base_image = self.resolve_image(raw_image)
            services: dict[str, Any] = {
                "postgres": {
                    "image": base_image,
                    "restart": "unless-stopped",
                    "environment": {
                        "POSTGRES_DB": "${POSTGRES_DB:-app}",
                        "POSTGRES_USER": "${POSTGRES_USER:-postgres}",
                        "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD}",
                        "POSTGRES_MAX_CONNECTIONS": str(self.max_connections),
                    },
                    "volumes": ["postgres_data:/var/lib/postgresql/data"],
                    "ports": [f"{self.ctx.host_port_map.get('postgres', 5432)}:5432"] if self.ctx.environment == "local" else [],
                    "healthcheck": self.health_check(),
                    "networks": [f"{project}_data"],
                    "labels": {"nikame.module": "postgres", "nikame.category": "database"},
                }
            }
        else:
            # HA/Replication case: Bitnami images are much easier to configure via env vars
            image = "public.ecr.aws/bitnami/postgresql:16.2.0"
            services = {
                "postgres": {
                    "image": image,
                    "restart": "unless-stopped",
                    "environment": {
                        "POSTGRESQL_DATABASE": "${POSTGRES_DB:-app}",
                        "POSTGRESQL_USERNAME": "${POSTGRES_USER:-postgres}",
                        "POSTGRESQL_PASSWORD": "${POSTGRES_PASSWORD}",
                        "POSTGRESQL_REPLICATION_MODE": "master",
                        "POSTGRESQL_REPLICATION_USER": "repl_user",
                        "POSTGRESQL_REPLICATION_PASSWORD": "${POSTGRES_PASSWORD}",
                        "POSTGRES_USER": "${POSTGRES_USER:-postgres}",
                        "POSTGRES_DB": "${POSTGRES_DB:-app}",  # Required for healthcheck consistency
                    },
                    "volumes": ["postgres_data:/bitnami/postgresql"],
                    "healthcheck": self.health_check(),
                    "networks": [f"{project}_data"],
                    "labels": {"nikame.module": "postgres", "nikame.role": "primary"},
                },
                "postgres-replica": {
                    "image": image,
                    "restart": "unless-stopped",
                    "depends_on": {"postgres": {"condition": "service_healthy"}},
                    "environment": {
                        "POSTGRESQL_USERNAME": "${POSTGRES_USER:-postgres}",
                        "POSTGRESQL_PASSWORD": "${POSTGRES_PASSWORD}",
                        "POSTGRESQL_MASTER_HOST": "postgres",
                        "POSTGRESQL_REPLICATION_MODE": "slave",
                        "POSTGRESQL_REPLICATION_USER": "repl_user",
                        "POSTGRESQL_REPLICATION_PASSWORD": "${POSTGRES_PASSWORD}",
                        "POSTGRESQL_DATABASE": "${POSTGRES_DB:-app}",
                        "POSTGRES_USER": "${POSTGRES_USER:-postgres}",
                        "POSTGRES_DB": "${POSTGRES_DB:-app}",
                    },
                    "networks": [f"{project}_data"],
                    "labels": {"nikame.module": "postgres", "nikame.role": "replica"},
                }
            }

        if self.pgbouncer:
            # Primary RW Pool
            services["pgbouncer"] = {
                "image": "public.ecr.aws/bitnami/pgbouncer:1.23.1",
                "restart": "unless-stopped",
                "environment": {
                    "POSTGRESQL_HOST": "postgres",
                    "POSTGRESQL_PORT": "5432",
                    "POSTGRESQL_USERNAME": "${POSTGRES_USER:-postgres}",
                    "POSTGRESQL_PASSWORD": "${POSTGRES_PASSWORD}",
                    "PGBOUNCER_DATABASE": "${POSTGRES_DB:-app}",
                    "PGBOUNCER_POOL_MODE": "transaction",
                    "PGBOUNCER_MAX_CLIENT_CONN": "1000",
                    "PGBOUNCER_DEFAULT_POOL_SIZE": "25",
                },
                "depends_on": {"postgres": {"condition": "service_healthy"}},
                "networks": [f"{project}_backend", f"{project}_data"],
                "labels": {"nikame.module": "pgbouncer", "nikame.role": "rw"},
            }
            
            # Secondary RO Pool (only if replicas exist)
            if self.replicas > 1:
                services["pgbouncer-ro"] = {
                    "image": "public.ecr.aws/bitnami/pgbouncer:1.23.1",
                    "restart": "unless-stopped",
                    "environment": {
                        "POSTGRESQL_HOST": "postgres-replica",
                        "POSTGRESQL_PORT": "5432",
                        "POSTGRESQL_USERNAME": "${POSTGRES_USER:-postgres}",
                        "POSTGRESQL_PASSWORD": "${POSTGRES_PASSWORD}",
                        "PGBOUNCER_DATABASE": "${POSTGRES_DB:-app}",
                        "PGBOUNCER_POOL_MODE": "transaction",
                        "PGBOUNCER_MAX_CLIENT_CONN": "1000",
                        "PGBOUNCER_DEFAULT_POOL_SIZE": "25",
                    },
                    "depends_on": {"postgres-replica": {"condition": "service_started"}},
                    "networks": [f"{project}_backend", f"{project}_data"],
                    "labels": {"nikame.module": "pgbouncer", "nikame.role": "ro"},
                }

        # Item 11: Daily Backup Service (Post-init, non-local)
        if self.ctx.environment != "local":
            services["postgres-backup"] = {
                "image": "public.ecr.aws/bitnami/postgresql:16.2.0",
                "restart": "unless-stopped",
                "environment": {
                    "POSTGRESQL_CLIENT_DATABASE": "${POSTGRES_DB:-app}",
                    "POSTGRESQL_CLIENT_USERNAME": "${POSTGRES_USER:-postgres}",
                    "POSTGRESQL_CLIENT_PASSWORD": "${POSTGRES_PASSWORD}",
                    "POSTGRESQL_HOST": "postgres",
                },
                "depends_on": {"postgres": {"condition": "service_healthy"}},
                "networks": [f"{project}_data"],
                "labels": {"nikame.module": "postgres", "nikame.role": "backup"},
                "entrypoint": ["/bin/bash", "-c", "while true; do pg_dump -h $POSTGRESQL_HOST -U $POSTGRESQL_CLIENT_USERNAME $POSTGRESQL_CLIENT_DATABASE > /backups/backup_$(date +%Y%m%d_%H%M%S).sql; sleep 86400; done"],
                "volumes": ["postgres_backups:/backups"],
            }

        return services

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate full production-ready K8s architecture for PostgreSQL."""
        name = "postgres"
        if self.replicas > 1:
            image = "public.ecr.aws/bitnami/postgresql:16.2.0"
        else:
            image = f"pgvector/pgvector:pg{self.version}" if getattr(self, "is_pgvector", False) else f"postgres:{self.version}-alpine"

        # 1. StatefulSet
        statefulset: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"app": name, "nikame.module": self.NAME},
            },
            "spec": {
                "serviceName": name,
                "replicas": self.replicas,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "serviceAccountName": name,
                        "containers": [
                            {
                                "name": name,
                                "image": image,
                                "ports": [{"containerPort": 5432}],
                                "envFrom": [{"secretRef": {"name": f"{name}-secret"}}],
                                "volumeMounts": [
                                    {"name": f"{name}-data", "mountPath": "/var/lib/postgresql/data"}
                                ],
                                "resources": self.resource_requirements(),
                                "livenessProbe": {
                                    "exec": {"command": ["pg_isready", "-U", "postgres"]},
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10,
                                },
                            }
                        ]
                    },
                },
                "volumeClaimTemplates": [
                    {
                        "metadata": {"name": f"{name}-data"},
                        "spec": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": self.storage}},
                        },
                    }
                ],
            },
        }

        # 2. Headless Service for StatefulSet
        headless_service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"app": name}
            },
            "spec": {
                "selector": {"app": name},
                "ports": [{"port": 5432, "targetPort": 5432}],
                "clusterIP": "None",
            },
        }

        # 3. Production Manifests
        manifests = [
            self.service_account(name),
            statefulset,
            headless_service,
            self.network_policy(name, allow_from=["api", "worker", "pgbouncer"]),
            self.pdb(name, min_available=1),
        ]

        # 4. pgBouncer pooling
        if self.pgbouncer:
            pb_name = "pgbouncer"
            pb_image = "public.ecr.aws/bitnami/pgbouncer:1.23.1"

            pb_dep: dict[str, Any] = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": pb_name,
                    "namespace": self.ctx.namespace,
                    "labels": {"app": pb_name}
                },
                "spec": {
                    "replicas": 2 if self.ctx.environment == "production" else 1,
                    "selector": {"matchLabels": {"app": pb_name}},
                    "template": {
                        "metadata": {"labels": {"app": pb_name}},
                        "spec": {
                            "serviceAccountName": name,
                            "containers": [
                                {
                                    "name": pb_name,
                                    "image": pb_image,
                                    "ports": [{"containerPort": 6432}],
                                    "envFrom": [{"secretRef": {"name": f"{name}-secret"}}],
                                    "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}},
                                }
                            ]
                        }
                    }
                }
            }
            pb_svc: dict[str, Any] = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": pb_name, "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"app": pb_name},
                    "ports": [{"port": 5432, "targetPort": 6432}]
                }
            }
            manifests.extend([pb_dep, pb_svc])

        # 5. Migration Job
        manifests.append(self.migration_job(
            name=name,
            image=f"{self.ctx.project_name}-api:latest",
            command=["alembic", "upgrade", "head"],
            env=[{"name": "DATABASE_URL", "value": f"postgresql+asyncpg://postgres@postgres:5432/{self.ctx.project_name}"}]
        ))

        # 6. Backup CronJob
        if self.ctx.environment != "local":
            cron_name = f"{name}-backup"
            manifests.append({
                "apiVersion": "batch/v1",
                "kind": "CronJob",
                "metadata": {
                    "name": cron_name,
                    "namespace": self.ctx.namespace,
                },
                "spec": {
                    "schedule": "0 2 * * *",
                    "jobTemplate": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [
                                        {
                                            "name": "backup",
                                            "image": "public.ecr.aws/bitnami/postgresql:16.2.0",
                                            "command": ["/bin/bash", "-c", f"pg_dump -h postgres -U postgres {self.ctx.project_name} > /backups/backup_$(date +%Y%m%d).sql"],
                                            "envFrom": [{"secretRef": {"name": f"{name}-secret"}}],
                                            "volumeMounts": [{"name": "backups", "mountPath": "/backups"}],
                                        }
                                    ],
                                    "restartPolicy": "OnFailure",
                                    "volumes": [
                                        {
                                            "name": "backups",
                                            "persistentVolumeClaim": {"claimName": f"{cron_name}-pvc"}
                                        }
                                    ],
                                }
                            }
                        }
                    }
                }
            })
            # Add PVC for backups
            manifests.append({
                "apiVersion": "v1",
                "kind": "PersistentVolumeClaim",
                "metadata": {"name": f"{cron_name}-pvc", "namespace": self.ctx.namespace},
                "spec": {
                    "accessModes": ["ReadWriteOnce"],
                    "resources": {"requests": {"storage": "20Gi"}}
                }
            })

        return manifests

    def health_check(self) -> dict[str, Any]:
        """PostgreSQL readiness probe."""
        return {
            "test": ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app}"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 10,
            "start_period": "60s",
        }

    def env_vars(self) -> dict[str, str]:
        """Connection env vars — routes through pgBouncer if enabled."""
        host = "pgbouncer" if self.pgbouncer else "postgres"
        port = "5432"
        
        vars = {
            "DATABASE_URL": f"postgresql+asyncpg://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@{host}:{port}/${{POSTGRES_DB}}",
            "POSTGRES_HOST": host,
            "POSTGRES_PORT": port,
        }
        
        if self.replicas > 1:
            read_host = "pgbouncer-ro" if self.pgbouncer else "postgres-replica"
            vars["DATABASE_READ_URL"] = f"postgresql+asyncpg://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@{read_host}:{port}/${{POSTGRES_DB}}"
            vars["POSTGRES_READ_HOST"] = read_host
            
        return vars

    def init_scripts(self) -> list[tuple[str, str]]:
        """Generate init SQL for requested extensions."""
        if not self.extensions:
            return []
        lines = ["-- Auto-generated by NIKAME"]
        for ext in self.extensions:
            lines.append(f"CREATE EXTENSION IF NOT EXISTS {ext};")
        return [("init.sql", "\n".join(lines))]

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alerts for PostgreSQL."""
        return [
            {
                "alert": "PostgresDown",
                "expr": "up{job='postgres'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {
                    "summary": "PostgreSQL is down",
                    "description": "PostgreSQL has been unreachable for over 1 minute.",
                },
            },
            {
                "alert": "PostgresHighConnections",
                "expr": "pg_stat_activity_count / pg_settings_max_connections > 0.8",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "PostgreSQL connections above 80%",
                    "description": "Connection utilization is critically high.",
                },
            },
            {
                "alert": "PostgresReplicationLag",
                "expr": "pg_replication_lag > 30",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "PostgreSQL replication lag > 30s",
                    "description": "Replication lag has exceeded 30 seconds.",
                },
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for PostgreSQL."""
        return {
            "title": f"{self.ctx.project_name} — PostgreSQL",
            "uid": "nikame-postgres",
            "panels": [
                {
                    "title": "Active Connections",
                    "type": "gauge",
                    "targets": [{"expr": "pg_stat_activity_count"}],
                },
                {
                    "title": "Transactions/sec",
                    "type": "timeseries",
                    "targets": [{"expr": "rate(pg_stat_database_xact_commit[5m])"}],
                },
                {
                    "title": "Cache Hit Ratio",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)"
                        }
                    ],
                },
                {
                    "title": "Database Size",
                    "type": "timeseries",
                    "targets": [{"expr": "pg_database_size_bytes"}],
                },
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cost (RDS equivalent)."""
        tier_costs = {"small": 25.0, "medium": 60.0, "large": 180.0, "xlarge": 400.0}
        return tier_costs.get(self.ctx.resource_tier, 60.0)

    def guide_metadata(self) -> dict[str, Any]:
        """Postgres-specific guide metadata."""
        port = self.ctx.host_port_map.get("postgres", 5432)
        return {
            "overview": self.DESCRIPTION,
            "urls": [
                {
                    "label": "PostgreSQL",
                    "url": f"localhost:{port}",
                    "usage": "Primary SQL database",
                    "creds": "postgres / ${POSTGRES_PASSWORD}"
                }
            ],
            "integrations": [
                {
                    "target": "FastAPI",
                    "description": "Connects via SQLAlchemy using the `POSTGRES_URL` env var."
                }
            ],
            "troubleshooting": [
                {
                    "issue": "Database connection refused",
                    "fix": "Run `nikame up` and check if the `postgres` container is healthy."
                },
                {
                    "issue": "Authentication failed",
                    "fix": "Ensure `POSTGRES_PASSWORD` in `.env` matches the one used during first start."
                }
            ],
        }

    def resource_requirements(self) -> dict[str, Any]:
        """K8s resource requests/limits for PostgreSQL."""
        return {
            "requests": {"cpu": "250m", "memory": "512Mi"},
            "limits": {"cpu": "1000m", "memory": "2Gi"},
        }
