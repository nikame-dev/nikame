"""BaseModule abstract class — THE CORE CONTRACT.

Every NIKAME module (Postgres, Redis, FastAPI, vLLM, etc.) inherits
from BaseModule and implements the required methods. This ensures
consistent output across all modules for Docker Compose, K8s
manifests, health checks, env vars, and observability configs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleContext:
    """Shared context passed to all modules during generation.

    Contains project-level information needed by every module to
    generate correct service names, network configs, and resource sizing.

    Attributes:
        project_name: Sanitized project name for labels and namespaces.
        environment: Deployment profile (local, staging, production).
        cloud: Cloud provider if applicable.
        namespace: Kubernetes namespace.
        domain: Custom domain for TLS and routing.
        tls_enabled: Whether TLS is configured.
        resource_tier: Resource sizing tier for cost estimation.
        all_env_vars: Accumulated env vars from all modules.
    """

    project_name: str
    environment: str = "local"
    cloud: str | None = None
    namespace: str = "default"
    domain: str | None = None
    tls_enabled: bool = False
    resource_tier: str = "medium"
    all_env_vars: dict[str, str] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    wiring: dict[str, Any] = field(default_factory=dict)
    active_modules: list[str] = field(default_factory=list)
    host_port_map: dict[str, int] = field(default_factory=dict)


class BaseModule(ABC):
    """Abstract base class for all NIKAME infrastructure modules.

    Every module must declare class-level metadata (NAME, CATEGORY, etc.)
    and implement compose_spec(), k8s_manifests(), and health_check()
    at minimum. Optional methods provide Grafana dashboards, Prometheus
    rules, Terraform resources, and cost estimates.

    Attributes:
        NAME: Module identifier used in nikame.yaml (e.g., "postgres").
        CATEGORY: Module category (e.g., "database", "cache").
        DESCRIPTION: Human-readable description.
        DEFAULT_VERSION: Default Docker image tag.
        DEPENDENCIES: List of module NAMEs this requires.
        CONFLICTS: List of module NAMEs that cannot coexist.
    """

    NAME: str
    CATEGORY: str
    DESCRIPTION: str
    DEFAULT_VERSION: str
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        """Initialize a module with its config and project context.

        Args:
            config: Module-specific configuration dict from nikame.yaml.
            ctx: Shared project context.
        """
        self.config = config
        self.ctx = ctx
        self.version: str = config.get("version", self.DEFAULT_VERSION)

    def dependencies(self) -> list[str]:
        """Return list of module names this module requires."""
        return list(self.DEPENDENCIES)

    def conflicts(self) -> list[str]:
        """Return list of module names incompatible with this one."""
        return list(self.CONFLICTS)

    @abstractmethod
    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service specification.

        Returns:
            Dict where keys are service names and values are
            Docker Compose service specs.
        """

    @abstractmethod
    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate Kubernetes resource manifests.

        Returns:
            List of K8s resource dicts (Deployment, Service,
            StatefulSet, PVC, ConfigMap, etc.).
        """

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Generate Docker Compose health check specification.

        Returns:
            Dict with test, interval, timeout, retries, start_period.
        """

    def env_vars(self) -> dict[str, str]:
        """Return environment variables for dependent services.

        Other services use these to auto-connect (e.g., DATABASE_URL).

        Returns:
            Dict of env var name → value template.
        """
        return {}

    def init_scripts(self) -> list[tuple[str, str]]:
        """Return initialization scripts for this module.

        Returns:
            List of (filename, content) tuples.
        """
        return []

    def prometheus_scrape_targets(self) -> list[dict[str, Any]]:
        """Return Prometheus scrape configurations for this module.
        
        Returns:
            List of dicts following the Prometheus scrape_config schema.
        """
        return []

    def scaffold_files(self) -> list[tuple[str, str]]:
        """Return application scaffold files for this module.

        These are typically source code files (e.g., main.py, Dockerfile)
        that get written to a project-specific directory (e.g., services/api/).

        Returns:
            List of (relative_path, content) tuples.
        """
        return []

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Return Grafana dashboard JSON for this module.

        Returns:
            Dashboard JSON dict, or None if not applicable.
        """
        return None

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Return Prometheus alerting rules for this module.

        Returns:
            List of Prometheus rule dicts.
        """
        return []

    def terraform_resources(self) -> dict[str, Any] | None:
        """Return Terraform resource blocks for cloud-managed equivalents.

        Returns:
            Terraform resource dict, or None if not applicable.
        """
        return None

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly cloud cost for this module.

        Returns:
            Cost in USD, or None if unknown.
        """
        return None

    def guide_metadata(self) -> dict[str, Any]:
        """Return metadata for GUIDE.md generation.
        
        Returns:
            Dict containing overview, urls, integrations, and troubleshooting.
        """
        return {
            "overview": self.DESCRIPTION,
            "urls": [],
            "integrations": [],
            "troubleshooting": [],
        }

    def resource_requirements(self) -> dict[str, Any]:
        """Return Kubernetes resource requests and limits.

        Returns:
            Dict with 'requests' and 'limits' sub-dicts.
        """
        # Tiered defaults
        tiers = {
            "small": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "200m", "memory": "256Mi"}},
            "medium": {"requests": {"cpu": "250m", "memory": "512Mi"}, "limits": {"cpu": "500m", "memory": "1Gi"}},
            "large": {"requests": {"cpu": "500m", "memory": "1Gi"}, "limits": {"cpu": "1000m", "memory": "2Gi"}},
            "xlarge": {"requests": {"cpu": "1000m", "memory": "2Gi"}, "limits": {"cpu": "2000m", "memory": "4Gi"}},
        }
        return tiers.get(self.ctx.resource_tier, tiers["medium"])

    # ──────────────────────────── K8s Helpers ────────────────────────────

    def hpa(self, name: str, min_reps: int = 1, max_reps: int = 10, cpu: int = 70, mem: int = 80) -> dict[str, Any]:
        """Generate HorizontalPodAutoscaler manifest."""
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": name, "namespace": self.ctx.namespace},
            "spec": {
                "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": name},
                "minReplicas": min_reps,
                "maxReplicas": max_reps,
                "metrics": [
                    {"type": "Resource", "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": cpu}}},
                    {"type": "Resource", "resource": {"name": "memory", "target": {"type": "Utilization", "averageUtilization": mem}}},
                ]
            }
        }

    def pdb(self, name: str, min_available: int = 1) -> dict[str, Any]:
        """Generate PodDisruptionBudget manifest."""
        return {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": {"name": name, "namespace": self.ctx.namespace},
            "spec": {
                "minAvailable": min_available,
                "selector": {"matchLabels": {"app": name}}
            }
        }

    def service_account(self, name: str) -> dict[str, Any]:
        """Generate ServiceAccount manifest."""
        return {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {"name": name, "namespace": self.ctx.namespace, "labels": {"app": name}}
        }

    def network_policy(self, name: str, allow_from: list[str] = None) -> dict[str, Any]:
        """Generate NetworkPolicy manifest (Default Deny + Whitelist)."""
        rules = []
        if allow_from:
            for source in allow_from:
                rules.append({"from": [{"podSelector": {"matchLabels": {"app": source}}}]})

        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": name, "namespace": self.ctx.namespace},
            "spec": {
                "podSelector": {"matchLabels": {"app": name}},
                "policyTypes": ["Ingress"],
                "ingress": rules
            }
        }

    def pvc(self, name: str, size: str = "10Gi") -> dict[str, Any]:
        """Generate PersistentVolumeClaim manifest."""
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": name, "namespace": self.ctx.namespace},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": size}}
            }
        }

    def ingress(self, name: str, host: str, path: str = "/", service_port: int = 80, tls_secret: str | None = None) -> dict[str, Any]:
        """Generate Ingress manifest."""
        annotations = {
            "kubernetes.io/ingress.class": "nginx",
            "nginx.ingress.kubernetes.io/ssl-redirect": "true",
            "traefik.ingress.kubernetes.io/router.entrypoints": "websecure",
        }

        spec = {
            "rules": [{
                "host": host,
                "http": {"paths": [{
                    "path": path,
                    "pathType": "Prefix",
                    "backend": {"service": {"name": name, "port": {"number": service_port}}}
                }]}
            }]
        }

        if tls_secret:
            spec["tls"] = [{"hosts": [host], "secretName": tls_secret}]

        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {"name": name, "namespace": self.ctx.namespace, "annotations": annotations},
            "spec": spec
        }

    def config_map(self, name: str, data: dict[str, str]) -> dict[str, Any]:
        """Generate ConfigMap manifest."""
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": name, "namespace": self.ctx.namespace},
            "data": data
        }

    def migration_job(self, name: str, image: str, command: list[str], env: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate K8s Job for database migrations."""
        return {
            "apiVersion": "v1",
            "kind": "Job",
            "metadata": {"name": f"{name}-migration", "namespace": self.ctx.namespace},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "migration",
                            "image": image,
                            "command": command,
                            "env": env
                        }],
                        "restartPolicy": "OnFailure"
                    }
                },
                "backoffLimit": 4
            }
        }

    def resource_quota(self, namespace: str, tier: str = "medium") -> dict[str, Any]:
        """Generate ResourceQuota manifest."""
        tiers = {
            "small": {"requests.cpu": "1", "requests.memory": "2Gi", "limits.cpu": "2", "limits.memory": "4Gi"},
            "medium": {"requests.cpu": "4", "requests.memory": "8Gi", "limits.cpu": "8", "limits.memory": "16Gi"},
            "large": {"requests.cpu": "16", "requests.memory": "32Gi", "limits.cpu": "32", "limits.memory": "64Gi"},
        }
        return {
            "apiVersion": "v1",
            "kind": "ResourceQuota",
            "metadata": {"name": "compute-resources", "namespace": namespace},
            "spec": {"hard": tiers.get(tier, tiers["medium"])}
        }

    def stateful_set(self, name: str, image: str, port: int, pvc_name: str, pvc_size: str, env_from: list[dict[str, Any]] = None, liveness_probe: dict[str, Any] = None) -> dict[str, Any]:
        """Generate a generic StatefulSet manifest."""
        return {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {"name": name, "namespace": self.ctx.namespace, "labels": {"app": name, "nikame.module": self.NAME}},
            "spec": {
                "serviceName": name,
                "replicas": 1,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "serviceAccountName": name,
                        "containers": [{
                            "name": name,
                            "image": image,
                            "ports": [{"containerPort": port}],
                            "envFrom": env_from or [],
                            "volumeMounts": [{"name": pvc_name, "mountPath": f"/var/lib/{name}"}],
                            "resources": self.resource_requirements(),
                            "livenessProbe": liveness_probe
                        }]
                    }
                },
                "volumeClaimTemplates": [{
                    "metadata": {"name": pvc_name},
                    "spec": {
                        "accessModes": ["ReadWriteOnce"],
                        "resources": {"requests": {"storage": pvc_size}}
                    }
                }]
            }
        }
    def init_container_wait(self, service_name: str, port: int = 5432) -> dict[str, Any]:
        """Generate an init container that waits for a service to be ready."""
        return {
            "name": f"wait-for-{service_name}",
            "image": "busybox:latest",
            "command": [
                "sh", "-c",
                f"until nc -z {service_name} {port}; do echo waiting for {service_name}; sleep 2; done;"
            ]
        }

    def sidecar_logging(self) -> dict[str, Any]:
        """Generate a Fluent-bit sidecar for logging."""
        return {
            "name": "fluent-bit",
            "image": "fluent/fluent-bit:latest",
            "ports": [{"containerPort": 24224}],
            "volumeMounts": [{"name": "varlog", "mountPath": "/var/log"}]
        }

    def node_port_service(self, name: str, port: int, node_port: int) -> dict[str, Any]:
        """Generate a NodePort service for developer access."""
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": f"{name}-nodeport", "namespace": self.ctx.namespace},
            "spec": {
                "type": "NodePort",
                "selector": {"app": name},
                "ports": [{
                    "port": port,
                    "targetPort": port,
                    "nodePort": node_port
                }]
            }
        }
