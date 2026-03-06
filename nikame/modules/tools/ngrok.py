"""Ngrok expose module for NIKAME.

Allows local development environments to be exposed publicly.
"""

from __future__ import annotations

from nikame.modules.base import BaseModule
from nikame.codegen.registry import register_module

@register_module
class NgrokModule(BaseModule):
    """Configuration for Ngrok local tunneling."""

    NAME = "ngrok"
    DESCRIPTION = "Secure tunneling to local localhost (local dev only)"
    CATEGORY = "tools"
    DEFAULT_PORT = 4040 # Ngrok agent API

    def get_service_config(self) -> dict[str, Any]:
        """Ngrok does not need a docker-compose service if run via pyngrok in FastAPI."""
        return {}

    def get_env_vars(self) -> dict[str, str]:
        return {
            "NGROK_AUTHTOKEN": "",
        }

    def get_dependencies(self) -> list[str]:
        return []
