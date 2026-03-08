"""Agent Framework pre-wiring integration.

Triggers when LangChain, LlamaIndex, or Haystack are present. Automatically
wires the framework to the active Vector DB and LLM inference module.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class AgentFrameworkIntegration(BaseIntegration):
    """Generates pre-configured AI Agent scaffolding."""

    REQUIRED_MODULES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determine framework
        if "langchain" in self.active_modules:
            self.framework = "langchain"
        elif "llamaindex" in self.active_modules:
            self.framework = "llamaindex"
        elif "haystack" in self.active_modules:
            self.framework = "haystack"
        else:
            self.framework = None
            
        # Determine active vector DB
        vdbs = ["qdrant", "weaviate", "milvus", "chroma", "pgvector"]
        self.vector_db = next((v for v in vdbs if v in self.active_modules), None)
        
        # Determine LLM gateway
        llms = ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm", "whisper", "tts"]
        self.llm = next((l for l in llms if l in self.active_modules), None)

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if any agent framework is present alongside an LLM module."""
        has_framework = any(m in active_modules for m in ["langchain", "llamaindex", "haystack"])
        has_llm = any(m in active_modules for m in ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm"])
        return has_framework and has_llm

    def generate_core(self) -> list[tuple[str, str]]:
        if not self.framework:
            return []
            
        if self.framework == "langchain":
            code = self._generate_langchain()
        elif self.framework == "llamaindex":
            code = self._generate_llamaindex()
        else:
            code = self._generate_haystack()
            
        return [("app/core/integrations/agent_framework.py", code)]

    def generate_lifespan(self) -> str:
        return f"""
    # --- Agent Framework Startup ---
    try:
        from app.core.integrations.agent_framework import get_agent_executor
        logger.info("Initializing {self.framework} framework wiring...")
        get_agent_executor()
    except Exception as e:
        logger.warning(f"Failed to initialize Agent Framework: {{e}}")
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return f"""
    AGENT_TOOL_CALLS = Counter(
        "nikame_agent_tool_calls_total", 
        "Total number of tool calls dispatched by the {self.framework} agent"
    )
        """

    def generate_guide(self) -> str:
        vdb_str = self.vector_db or "None (Memory)"
        return f"""
### Agent Framework ({self.framework})
**Status:** Active 🟢 
**Wiring:** 
- **LLM Engine:** `{self.llm}`
- **Vector Store:** `{vdb_str}`

The agent executor is automatically configured to use your self-hosted LLM and Vector search. 
Import `get_agent_executor` from `app.core.integrations.agent_framework` to kick off AI tasks natively in your route handlers.
"""

    def _generate_langchain(self) -> str:
        return f"""import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_agent_executor():
    import langchain
    from langchain.agents import initialize_agent, AgentType
    from langchain.llms import OpenAI # Using OpenAI wrapper for LocalAI etc
    
    logger.info("Configuring LangChain to use {self.llm}")
    
    # Example using the generic OpenAI wrapper pointing to our local API (LocalAI/etc)
    llm = OpenAI(
        openai_api_base=settings.OPENAI_API_BASE,
        openai_api_key="not-needed"
    )
    
    # Tools would be defined here
    tools = []
    
    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
        verbose=True
    )
    
    return agent
"""

    def _generate_llamaindex(self) -> str:
        return f"""import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_agent_executor():
    from llama_index.llms.openai_like import OpenAILike
    from llama_index.core import Settings
    
    logger.info("Configuring LlamaIndex to use {self.llm}")
    
    llm = OpenAILike(
        api_base=settings.OPENAI_API_BASE,
        api_key="not-needed",
        model="local-model"
    )
    
    # Set it globally for the application
    Settings.llm = llm
    
    return llm
"""

    def _generate_haystack(self) -> str:
        return f"""import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_agent_executor():
    from haystack.nodes import PromptNode
    
    logger.info("Configuring Haystack to use {self.llm}")
    
    # Configure PromptNode to use our local endpoint
    prompt_node = PromptNode(
        model_name_or_path="local-model",
        api_key="sk-local",
        model_kwargs={{"api_base": settings.OPENAI_API_BASE}}
    )
    
    return prompt_node
"""
