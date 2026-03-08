"""DVC data versioning module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class DVCModule(BaseModule):
    """DVC module for data versioning.

    Configures DVC to use MinIO as a remote storage backend.
    """

    NAME = "dvc"
    CATEGORY = "ml"
    DESCRIPTION = "DVC for data versioning with MinIO/S3 remote"
    DEFAULT_VERSION = "latest"

    def compose_spec(self) -> dict[str, Any]:
        """DVC is a client tool, no server-side compose spec needed."""
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """DVC is a client tool, no K8s manifests needed."""
        return []

    def scaffold_files(self) -> list[tuple[str, str]]:
        """Generate DVC configuration files."""
        dvc_config = f"""[core]
    remote = minio
['remote "minio"']
    url = s3://dvc
    endpointurl = http://minio:9000
    access_key_id = minioadmin
    secret_access_key = minioadmin
    use_ssl = false
"""
        return [
            (".dvc/config", dvc_config),
        ]

    def health_check(self) -> dict[str, Any]:
        """DVC is a client tool, no server-side health check."""
        return {}


register_module(DVCModule)
