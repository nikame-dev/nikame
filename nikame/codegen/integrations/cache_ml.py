"""GPTCache Semantic Caching Integration.

Triggers when GPTCache is active. Automatically drops in a Two-Tier caching
strategy if caching infrastructure (Redis/Dragonfly) and Vector databases are found.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class GPTCacheIntegration(BaseIntegration):
    """Generates the advanced semantic LLM caching layer."""

    REQUIRED_MODULES = ["gptcache"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determine exact match cache backend
        self.exact_backend = "sqlite"
        if "dragonfly" in self.active_modules or "redis" in self.active_modules:
            self.exact_backend = "redis"
            
        # Determine semantic match vector backend
        vdbs = ["qdrant", "weaviate", "milvus", "chroma", "pgvector"]
        self.vector_backend = "faiss" # default local
        for v in vdbs:
            if v in self.active_modules:
                self.vector_backend = v
                break

    def generate_core(self) -> list[tuple[str, str]]:
        caching_service = self._generate_caching_impl()
        return [("app/core/integrations/semantic_cache.py", caching_service)]

    def generate_lifespan(self) -> str:
        return """
    # --- Semantic Cache Integration Startup ---
    try:
        from app.core.integrations.semantic_cache import init_semantic_cache
        init_semantic_cache()
    except Exception as e:
        logger.warning(f"Failed to initialize semantic LLM cache: {e}")
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return """
    LLM_CACHE_HITS = Counter(
        "nikame_llm_cache_hits_total", 
        "Count of semantic cache hits for LLM requests"
    )
    LLM_CACHE_MISSES = Counter(
        "nikame_llm_cache_misses_total",
        "Count of semantic cache misses for LLM requests"
    )
        """

    def generate_guide(self) -> str:
        return f"""
### Semantic LLM Caching (GPTCache)
**Status:** Active 🟢 
**Two-Tier Strategy:** 
- **Exact Match Store:** `{self.exact_backend}`
- **Semantic Vector Store:** `{self.vector_backend}`

All LLM gateway calls are automatically routed through `GPTCache`. 
1. The engine checks `{self.exact_backend}` for an exact text match.
2. If missed, it embeds the prompt and searches `{self.vector_backend}` for semantic similarity.
3. If missed again, it invokes the actual LLM and caches the pair.
"""

    def _generate_caching_impl(self) -> str:
        vdb_imports = ""
        vdb_init = 'VectorBase("faiss", dimension=1536)'
        
        if self.vector_backend == "qdrant":
            vdb_init = 'VectorBase("qdrant", dimension=1536, host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, collection_name="gptcache")'
        elif self.vector_backend == "milvus":
            vdb_imports = "from gptcache.manager.vector_data.milvus import Milvus"
            vdb_init = 'VectorBase("milvus", dimension=1536, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)'
        elif self.vector_backend == "weaviate":
            vdb_init = 'VectorBase("weaviate", dimension=1536, url=settings.WEAVIATE_URL)'
        elif self.vector_backend == "chroma":
            vdb_init = 'VectorBase("chromadb", dimension=1536)'
            
        exact_init = 'CacheBase("sqlite")'
        if self.exact_backend == "redis":
            exact_init = 'CacheBase("redis", url=settings.REDIS_URL)'

        return f"""import logging
from gptcache import cache
from gptcache.manager import get_data_manager, CacheBase, VectorBase
from gptcache.processor.pre import get_prompt
from app.core.config import settings
{vdb_imports}

logger = logging.getLogger(__name__)

def init_semantic_cache():
    \"\"\"Initialize GPTCache two-tier strategy based on active infrastructure.\"\"\"
    logger.info("Initializing multi-tier GPTCache...")
    try:
        # Cache Base: {self.exact_backend}
        # Vector Base: {self.vector_backend}
        data_manager = get_data_manager(
            {exact_init},
            {vdb_init}
        )
        cache.init(
            pre_embedding_func=get_prompt,
            data_manager=data_manager,
        )
        logger.info("Semantic cache ready.")
    except Exception as e:
        logger.error(f"Error configuring GPTCache backends: {{e}}")
"""
