"""MongoDB database module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class MongoDBModule(BaseModule):
    """MongoDB NoSQL database module."""

    NAME = "mongodb"
    CATEGORY = "database"
    DESCRIPTION = "MongoDB document-oriented NoSQL database"
    DEFAULT_VERSION = "7.0"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.root_user: str = config.get("root_user", "admin")
        self.replicas: int = config.get("replicas", 1)

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for MongoDB."""
        return {
            "mongodb": {
                "image": f"mongo:{self.version}",
                "restart": "unless-stopped",
                "ports": ["27017:27017"],
                "environment": {
                    "MONGO_INITDB_ROOT_USERNAME": self.root_user,
                    "MONGO_INITDB_ROOT_PASSWORD": "${MONGODB_ROOT_PASSWORD}",
                },
                "volumes": ["mongodb_data:/data/db"],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s StatefulSet for MongoDB."""
        # Simple StatefulSet implementation
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {"name": "mongodb", "namespace": self.ctx.namespace},
                "spec": {
                    "serviceName": "mongodb",
                    "replicas": self.replicas,
                    "selector": {"matchLabels": {"app": "mongodb"}},
                    "template": {
                        "metadata": {"labels": {"app": "mongodb"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "mongodb",
                                    "image": f"mongo:{self.version}",
                                    "ports": [{"containerPort": 27017}],
                                    "env": [
                                        {"name": "MONGO_INITDB_ROOT_USERNAME", "value": self.root_user},
                                        {
                                            "name": "MONGO_INITDB_ROOT_PASSWORD",
                                            "valueFrom": {"secretKeyRef": {"name": "mongodb-secrets", "key": "password"}},
                                        },
                                    ],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Docker Compose health check."""
        return {
            "test": ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose MONGODB_URL."""
        return {
            "MONGODB_URL": f"mongodb://{self.root_user}:${{MONGODB_ROOT_PASSWORD}}@mongodb:27017",
        }
