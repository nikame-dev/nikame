"""HashiCorp Vault secret management module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import register_module


class VaultModule(BaseModule):
    """HashiCorp Vault module."""

    NAME = "vault"
    CATEGORY = "auth"
    DESCRIPTION = "Vault for secret management and encryption-as-a-service"
    DEFAULT_VERSION = "1.15"

    def required_ports(self) -> dict[str, int]:
        """Ports for HashiCorp Vault API."""
        return {"vault": 8200}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Vault."""
        return {
            "vault": {
                "image": f"hashicorp/vault:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('vault', 8200)}:8200"] if self.ctx.environment == "local" else [],
                "environment": {
                    "VAULT_DEV_ROOT_TOKEN_ID": "root",
                    "VAULT_DEV_LISTEN_ADDRESS": "0.0.0.0:8200",
                },
                "cap_add": ["IPC_LOCK"],
                "networks": [
                    f"{self.ctx.project_name}_backend",
                    f"{self.ctx.project_name}_data",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": self.NAME,
                    "nikame.category": self.CATEGORY,
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment and Service for Vault."""
        name = self.NAME
        manifests = []

        # 1. Service Account
        manifests.append({
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"nikame.module": name}
            }
        })

        # 2. Service
        manifests.append({
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"nikame.module": name}
            },
            "spec": {
                "ports": [{"port": 8200, "targetPort": 8200, "name": "http"}],
                "selector": {"nikame.module": name}
            }
        })

        # 3. PersistentVolumeClaim
        manifests.append({
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{name}-data",
                "namespace": self.ctx.namespace,
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": "1Gi"}}
            }
        })

        # 4. Deployment
        manifests.append({
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"nikame.module": name}
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"nikame.module": name}},
                "template": {
                    "metadata": {"labels": {"nikame.module": name}},
                    "spec": {
                        "serviceAccountName": name,
                        "containers": [
                            {
                                "name": name,
                                "image": f"hashicorp/vault:{self.version}",
                                "args": ["server", "-dev", "-dev-root-token-id=root"],
                                "ports": [{"containerPort": 8200}],
                                "env": [
                                    {"name": "VAULT_ADDR", "value": "http://0.0.0.0:8200"},
                                    {"name": "VAULT_API_ADDR", "value": "http://0.0.0.0:8200"},
                                ],
                                "volumeMounts": [
                                    {"name": "data", "mountPath": "/vault/data"}
                                ],
                                "securityContext": {
                                    "capabilities": {"add": ["IPC_LOCK"]}
                                }
                            }
                        ],
                        "volumes": [
                            {"name": "data", "persistentVolumeClaim": {"claimName": f"{name}-data"}}
                        ]
                    },
                },
            },
        })
        return manifests

    def health_check(self) -> dict[str, Any]:
        """Vault health check."""
        return {
            "test": ["CMD", "vault", "status"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose VAULT_ADDR."""
        return {"VAULT_ADDR": f"http://vault.{self.ctx.namespace}.svc.cluster.local:8200", "VAULT_TOKEN": "root"}

register_module(VaultModule)
