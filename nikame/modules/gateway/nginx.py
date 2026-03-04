"""Nginx gateway module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class NginxModule(BaseModule):
    """Nginx reverse proxy and gateway module."""

    NAME = "nginx"
    CATEGORY = "gateway"
    DESCRIPTION = "Nginx high-performance HTTP server and reverse proxy"
    DEFAULT_VERSION = "1.25"

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for Nginx."""
        return {
            "nginx": {
                "image": f"nginx:{self.version}-alpine",
                "restart": "unless-stopped",
                "ports": ["80:80", "443:443"],
                "volumes": [
                    "configs/nginx/nginx.conf:/etc/nginx/nginx.conf:ro",
                ],
                "networks": [f"{self.ctx.project_name}_network"],
                "healthcheck": self.health_check(),
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """K8s Deployment for Nginx."""
        return [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "nginx", "namespace": self.ctx.namespace},
                "spec": {
                    "selector": {"matchLabels": {"app": "nginx"}},
                    "template": {
                        "metadata": {"labels": {"app": "nginx"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "nginx",
                                    "image": f"nginx:{self.version}-alpine",
                                    "ports": [{"containerPort": 80}],
                                }
                            ]
                        },
                    },
                },
            }
        ]

    def health_check(self) -> dict[str, Any]:
        """Nginx health check."""
        return {
            "test": ["CMD", "nginx", "-t"],
            "interval": "30s",
        }

    def init_scripts(self) -> list[tuple[str, str]]:
        """Provide a default nginx.conf."""
        conf = """
user  nginx;
worker_processes  auto;
error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;
events {
    worker_connections  1024;
}
http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;
    server {
        listen       80;
        server_name  localhost;
        location / {
            root   /usr/share/nginx/html;
            index  index.html index.htm;
        }
    }
}
"""
        return [("nginx.conf", conf)]
