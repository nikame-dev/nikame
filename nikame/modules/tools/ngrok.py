"""Ngrok expose module for NIKAME.

Allows local development environments to be exposed publicly.
"""

from __future__ import annotations

from nikame.modules.base import BaseModule
from nikame.modules.registry import register_module

@register_module
class NgrokModule(BaseModule):
    """Configuration for Ngrok local tunneling."""

    NAME = "ngrok"
    DESCRIPTION = "Secure tunneling to local localhost (local dev only)"
    CATEGORY = "tools"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 4040 # Ngrok agent API

    def required_ports(self) -> dict[str, int]:
        """Ngrok agent API port."""
        return {"ngrok": self.DEFAULT_PORT}

    def compose_spec(self) -> dict[str, Any]:
        """Ngrok does not need a docker-compose service if run via pyngrok in FastAPI."""
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Ngrok is local-only."""
        return []

    def health_check(self) -> dict[str, Any]:
        """Default healthy."""
        return {}

    def env_vars(self) -> dict[str, str]:
        return {
            "NGROK_AUTHTOKEN": "",
        }

    def guide_metadata(self) -> dict[str, Any]:
        """Ngrok-specific guide metadata."""
        return {
            "overview": self.DESCRIPTION,
            "urls": [
                {
                    "label": "Ngrok Agent API",
                    "url": "http://localhost:4040",
                    "usage": "Inspect local tunnel traffic",
                    "creds": "None"
                }
            ],
            "feature_guides": [
                {
                    "title": "Exposing your API with Ngrok",
                    "content": "To share your local API with others, ensure you have set `NGROK_AUTHTOKEN` in your `.env` file. When you run `nikame up`, a public tunnel will be created automatically, and the URL will be printed in the FastAPI logs."
                }
            ],
            "troubleshooting": [
                {
                    "issue": "Ngrok tunnel failed to start",
                    "fix": "Check if your `NGROK_AUTHTOKEN` is valid and that you aren't exceeding your plan's tunnel limits."
                }
            ],
        }
