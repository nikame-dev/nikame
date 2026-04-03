from nikame.modules.registry import register_module
from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class LlamaIndexModule(BaseModule):
    """
    LlamaIndex module for data-augmented LLM applications.
    """

    NAME = "llamaindex"
    CATEGORY = "ml"
    DESCRIPTION = "Data framework for LLM applications"
    DEFAULT_VERSION = "latest"

    def required_ports(self) -> dict[str, int]:
        return {}

    def compose_spec(self) -> dict[str, Any]:
        return {}

    def health_check(self) -> dict[str, Any]:
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []

