"""ArgoCD GitOps module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class ArgoCDModule(BaseModule):
    """ArgoCD GitOps module."""

    NAME = "argocd"
    CATEGORY = "cicd"
    DESCRIPTION = "ArgoCD declarative, GitOps continuous delivery tool for Kubernetes"
    DEFAULT_VERSION = "v2.10.1"

    def compose_spec(self) -> dict[str, Any]:
        """ArgoCD usually runs in K8s, but we provide a basic compose for dev."""
        return {
            "argocd": {
                "image": f"quay.io/argoproj/argocd:{self.version}",
                "restart": "unless-stopped",
                "ports": ["8083:8080"],
                "networks": [f"{self.ctx.project_name}_network"],
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Namespace for ArgoCD (minimal)."""
        return [
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": "argocd"},
            }
        ]

    def env_vars(self) -> dict[str, str]:
        """Expose ARGOCD_URL."""
        return {"ARGOCD_URL": "http://argocd-server:80"}
