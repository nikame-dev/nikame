from nikame.modules.registry import register_module
from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class GPTCacheModule(BaseModule):
    """
    GPTCache semantic caching module for LLM responses.
    """

    NAME = "gptcache"
    CATEGORY = "ml"
    DESCRIPTION = "Semantic caching for LLMs (Two-tier strategy)"
    DEFAULT_VERSION = "latest"

    def required_ports(self) -> dict[str, int]:
        """No dedicated ports; uses Redis/Dragonfly backend."""
        return {}

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.embedding_dimension = config.get("dimension", 1536)

    def compose_spec(self) -> dict[str, Any]:
        """
        GPTCache is typically an in-app library, but we can provide 
        sidecar or monitoring services if needed.
        """
        return {}

    def health_check(self) -> dict[str, Any]:
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []
