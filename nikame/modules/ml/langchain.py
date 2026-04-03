from nikame.modules.registry import register_module
from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class LangchainModule(BaseModule):
    """
    LangChain module for agentic workflows and LLM orchestration.
    
    Typically an in-app library, but can be configured with 
    tracing (LangSmith) or specific callbacks.
    """

    NAME = "langchain"
    CATEGORY = "ml"
    DESCRIPTION = "Agentic LLM orchestration and chain management"
    DEFAULT_VERSION = "latest"

    def required_ports(self) -> dict[str, int]:
        """LangChain itself has no ports (library)."""
        return {}

    def compose_spec(self) -> dict[str, Any]:
        """
        LangChain is integrated into the application code.
        No dedicated sidecars required for basic usage.
        """
        return {}

    def health_check(self) -> dict[str, Any]:
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []

    def guide_metadata(self) -> dict[str, Any]:
        return {
            "overview": "LangChain is the orchestrator for your LLM agents.",
            "urls": [
                {"name": "Documentation", "url": "https://python.langchain.com/"}
            ],
            "integrations": [
                "Auto-configured with LLM Gateway",
                "Ready for LangSmith tracing (set LANGCHAIN_TRACING_V2=true)"
            ],
            "troubleshooting": [
                "Ensure OpenAI or HubbingFace API keys are set in .env"
            ]
        }

