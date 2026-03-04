"""Kubernetes manifest composer for NIKAME.

Collects K8s resource definitions from all modules and merges them
into a single multi-document YAML file.
"""

from __future__ import annotations

from typing import Any

import yaml

from nikame.blueprint.engine import Blueprint


def generate_manifests(blueprint: Blueprint) -> str:
    """Generate a multi-document K8s manifest YAML string.

    Args:
        blueprint: Resolved blueprint containing all module instances.

    Returns:
        YAML string with '---' separators between resources.
    """
    all_manifests = blueprint.k8s_manifests()

    if not all_manifests:
        return ""

    # Sort manifests by Kind to ensure consistent output
    kind_order = {
        "Namespace": 0,
        "ResourceQuota": 1,
        "NetworkPolicy": 2,
        "ServiceAccount": 3,
        "SealedSecret": 4,
        "Secret": 5,
        "ConfigMap": 6,
        "PersistentVolume": 7,
        "PersistentVolumeClaim": 8,
        "Service": 9,
        "StatefulSet": 10,
        "Deployment": 11,
        "Job": 12,
        "CronJob": 13,
        "PodDisruptionBudget": 14,
        "HorizontalPodAutoscaler": 15,
        "Ingress": 16,
    }

    def _get_order(m: dict[str, Any]) -> int:
        return kind_order.get(m.get("kind", ""), 99)

    all_manifests.sort(key=_get_order)

    # Convert to multi-document YAML
    output = []
    for manifest in all_manifests:
        yaml_str = yaml.dump(
            manifest,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        output.append(f"---\n# {manifest.get('kind')}: {manifest.get('metadata', {}).get('name')}\n{yaml_str}")

    return "\n".join(output)
