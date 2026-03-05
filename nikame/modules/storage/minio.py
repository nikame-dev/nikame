"""MinIO object storage module.

S3-compatible object storage for local development and self-hosted deployments.
Includes the MinIO Console web UI for bucket management.
"""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class MinIOModule(BaseModule):
    """MinIO S3-compatible object storage module.

    Auto-creates configured buckets and provides an admin Console UI.
    """

    NAME = "minio"
    CATEGORY = "storage"
    DESCRIPTION = "MinIO S3-compatible object storage"
    DEFAULT_VERSION = "latest"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.buckets: list[str] = config.get("buckets", ["uploads", "backups"])

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for MinIO."""
        return {
            "minio": {
                "image": f"minio/minio:{self.version}",
                "restart": "unless-stopped",
                "command": "server /data --console-address ':9001'",
                "environment": {
                    "MINIO_ROOT_USER": "${MINIO_ROOT_USER:-minioadmin}",
                    "MINIO_ROOT_PASSWORD": "${MINIO_ROOT_PASSWORD}",
                },
                "ports": (
                    ["9000:9000", "9001:9001"]
                    if self.ctx.environment == "local"
                    else []
                ),
                "volumes": ["minio_data:/data"],
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "minio",
                    "nikame.category": "storage",
                },
            },
            "minio-init": {
                "image": "minio/mc:latest",
                "depends_on": {"minio": {"condition": "service_healthy"}},
                "entrypoint": "/bin/sh",
                "command": self._bucket_init_command(),
                "networks": [f"{self.ctx.project_name}_network"],
            },
        }

    def _bucket_init_command(self) -> str:
        """Generate mc commands to create buckets."""
        cmds = [
            "-c",
            " && ".join(
                [
                    "mc alias set myminio http://minio:9000 $${MINIO_ROOT_USER:-minioadmin} $${MINIO_ROOT_PASSWORD}",
                    *[f"mc mb --ignore-existing myminio/{bucket}" for bucket in self.buckets],
                ]
            ),
        ]
        return cmds[-1]

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate full production-ready K8s architecture for MinIO."""
        name = "minio"
        image = f"minio/minio:{self.version}"

        # 1. StatefulSet
        ss = self.stateful_set(
            name=name,
            image=image,
            port=9000,
            pvc_name=f"{name}-data",
            pvc_size="20Gi",
            liveness_probe={"httpGet": {"path": "/minio/health/live", "port": 9000}, "initialDelaySeconds": 20}
        )
        # Add Console port to StatefulSet (manual fix for MinIO double-port)
        ss["spec"]["template"]["spec"]["containers"][0]["ports"].append({"containerPort": 9001, "name": "console"})
        ss["spec"]["template"]["spec"]["containers"][0]["args"] = ["server", "/var/lib/minio", "--console-address", ":9001"]

        # 2. Service
        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name, "namespace": self.ctx.namespace, "labels": {"app": name}},
            "spec": {
                "selector": {"app": name},
                "ports": [
                    {"port": 9000, "targetPort": 9000, "name": "api"},
                    {"port": 9001, "targetPort": 9001, "name": "console"},
                ],
            },
        }

        # 3. Production Manifests
        manifests = [
            self.service_account(name),
            ss,
            service,
            self.network_policy(name, allow_from=["api", "worker"]),
            self.pdb(name, min_available=1),
        ]

        if self.ctx.domain:
            manifests.append(self.ingress(f"{name}-console", f"console.{self.ctx.domain}", service_port=9001, tls_secret=f"{name}-tls"))

        return manifests

    def health_check(self) -> dict[str, Any]:
        """MinIO health endpoint."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"],
            "interval": "15s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """S3-compatible env vars."""
        return {
            "S3_ENDPOINT": "http://minio:9000",
            "S3_ACCESS_KEY": "${MINIO_ROOT_USER:-minioadmin}",
            "S3_SECRET_KEY": "${MINIO_ROOT_PASSWORD}",
            "S3_BUCKET": self.buckets[0] if self.buckets else "uploads",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for MinIO."""
        return [
            {
                "alert": "MinIODown",
                "expr": "up{job='minio'} == 0",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "MinIO is down"},
            },
            {
                "alert": "MinIODiskUsageHigh",
                "expr": "minio_disk_storage_used_bytes / minio_disk_storage_total_bytes > 0.85",
                "for": "10m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "MinIO disk usage above 85%"},
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for MinIO."""
        return {
            "title": f"{self.ctx.project_name} — MinIO",
            "uid": "nikame-minio",
            "panels": [
                {"title": "Disk Usage", "type": "gauge", "targets": [{"expr": "minio_disk_storage_used_bytes"}]},
                {"title": "Objects Count", "type": "stat", "targets": [{"expr": "minio_bucket_objects_count"}]},
                {"title": "Requests/sec", "type": "timeseries", "targets": [{"expr": "rate(minio_http_requests_total[5m])"}]},
                {"title": "Network I/O", "type": "timeseries", "targets": [{"expr": "rate(minio_network_sent_bytes_total[5m])"}]},
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cost."""
        return 10.0
