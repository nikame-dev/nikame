"""Elasticsearch search database module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule


@register_module
class ElasticsearchModule(BaseModule):
    """Elasticsearch search engine module."""

    NAME = "elasticsearch"
    CATEGORY = "database"
    DESCRIPTION = "Elasticsearch distributed, RESTful search and analytics engine"
    DEFAULT_VERSION = "8.12.0"

    def required_ports(self) -> dict[str, int]:
        """Standard Elasticsearch port."""
        return {"elasticsearch": 9200}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Elasticsearch."""
        return {
            "elasticsearch": {
                "image": f"docker.elastic.co/elasticsearch/elasticsearch:{self.version}",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('elasticsearch', 9200)}:9200"] if self.ctx.environment == "local" else [],
                "environment": {
                    "discovery.type": "single-node",
                    "xpack.security.enabled": "false",
                    "ES_JAVA_OPTS": "-Xms512m -Xmx512m",
                },
                "volumes": ["elasticsearch_data:/usr/share/elasticsearch/data"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Elasticsearch."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {"name": "elasticsearch", "namespace": self.ctx.namespace},
                "spec": {
                    "serviceName": "elasticsearch",
                    "replicas": 1,
                    "selector": {"matchLabels": {"app": "elasticsearch"}},
                    "template": {
                        "metadata": {"labels": {"app": "elasticsearch"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "elasticsearch",
                                    "image": f"docker.elastic.co/elasticsearch/elasticsearch:{self.version}",
                                    "ports": [{"containerPort": 9200}],
                                    "env": [
                                        {"name": "discovery.type", "value": "single-node"},
                                        {"name": "xpack.security.enabled", "value": "false"},
                                    ],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Elasticsearch health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"],
            "interval": "30s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose ELASTICSEARCH_URL."""
        return {"ELASTICSEARCH_URL": "http://elasticsearch:9200"}
