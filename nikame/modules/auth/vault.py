"""HashiCorp Vault secret management module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class VaultModule(BaseModule):
    """HashiCorp Vault module."""

    NAME = "vault"
    CATEGORY = "auth"
    DESCRIPTION = "Vault for secret management and encryption-as-a-service"
    DEFAULT_VERSION = "1.15"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Vault."""
        return {
            "vault": {
                "image": f"hashicorp/vault:{self.version}",
                "restart": "unless-stopped",
                "ports": ["8200:8200"],
                "environment": {
                    "VAULT_DEV_ROOT_TOKEN_ID": "root",
                    "VAULT_DEV_LISTEN_ADDRESS": "0.0.0.0:8200",
                },
                "cap_add": ["IPC_LOCK"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Vault."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "vault", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "vault"}},
                    "template": {
                        "metadata": {"labels": {"app": "vault"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "vault",
                                    "image": f"hashicorp/vault:{self.version}",
                                    "ports": [{"containerPort": 8200}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Vault health check."""
        return {
            "test": ["CMD", "vault", "status"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose VAULT_ADDR."""
        return {"VAULT_ADDR": "http://vault:8200", "VAULT_TOKEN": "root"}
