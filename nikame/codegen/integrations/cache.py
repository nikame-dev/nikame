"""Cache-Aside Integration (Dragonfly + Postgres)

Triggers when Dragonfly (Redis) and Postgres are present. Provides
a seamless decorator/wrapper for caching database queries with automatic 
invalidation and configurable TTLs based on the OptimizationProfile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from collections import defaultdict

from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class CacheAsideIntegration(BaseIntegration):
    """Generates the Cache-Aside data access pattern."""

    REQUIRED_MODULES = ["dragonfly", "postgres"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if Multi-Tenancy is enabled for tenant-scoped keys
        self.is_multitenant = "multi_tenancy" in self.active_features

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        
        # 1. Caching Decorator Service
        cache_service = self._generate_cache_aside_py()
        files.append(("app/core/integrations/cache_aside.py", cache_service))

        return files

    def generate_lifespan(self) -> str:
        return """
    # --- Cache-Aside Integration Startup ---
    # Ping Dragonfly to ensure cache layer is hot
    from app.services.cache import DragonflyService
    await DragonflyService.ping()
        """

    def generate_health(self) -> dict[str, str]:
        return {
            "cache_aside_ratio": "await get_cache_hit_ratio()"
        }

    def generate_metrics(self) -> str:
        return """
    CACHE_HITS = Counter("nikame_cache_hits_total", "Total cache hits")
    CACHE_MISSES = Counter("nikame_cache_misses_total", "Total cache misses")
        """

    def generate_guide(self) -> str:
        guide = f"""
### Cache-Aside Integration
**Status:** Active 🟢
**Components:** Postgres + Dragonfly
**Tuning:** TTL set to {self.profile.cache_ttl_seconds}s (optimized for {self.profile.access_pattern})

The Matrix Engine has automatically injected a cache-aside layer. Wrap any expensive database repository calls with `@cache_query(prefix="users")`.
"""
        if self.is_multitenant:
            guide += "*Because multi-tenancy is active, all cache keys will be automatically prefixed with the current active tenant ID to prevent cross-tenant data leakage.*"
            
        return guide

    def _generate_cache_aside_py(self) -> str:
        tenant_prefix = 'f"{tenant_id}:" if tenant_id else ""' if self.is_multitenant else '""'
        tenant_arg = ", tenant_id: str = None" if self.is_multitenant else ""
        
        return f"""import json
import logging
from functools import wraps
from typing import Any, Callable

from app.services.cache import DragonflyService

logger = logging.getLogger(__name__)

# Configured by MatrixEngine OptimizationProfile
DEFAULT_TTL = {self.profile.cache_ttl_seconds}

def cache_query(prefix: str{tenant_arg}, ttl: int = DEFAULT_TTL):
    \"\"\"Decorator that implements the cache-aside pattern.\"\"\"
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Construct key
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{{k}}={{v!r}}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            
            tenant_str = {tenant_prefix}
            cache_key = f"{{tenant_str}}{{prefix}}:{{func.__name__}}:{{signature}}"
            
            # 1. Check Cache
            cached_result = await DragonflyService.get(cache_key)
            if cached_result:
                # Prometheus Metric: CACHE_HITS.inc()
                return json.loads(cached_result)
                
            # Prometheus Metric: CACHE_MISSES.inc()
            
            # 2. Cache Miss: Execute DB Query
            result = await func(*args, **kwargs)
            
            # 3. Store in Cache
            if result is not None:
                # Assuming objects are dict-serializable for this stub
                await DragonflyService.set(cache_key, json.dumps(result), expire=ttl)
                
            return result
        return wrapper
    return decorator

async def invalidate_cache(prefix: str{tenant_arg}):
    \"\"\"Invalidate all keys matching the prefix pattern.\"\"\"
    tenant_str = {tenant_prefix}
    pattern = f"{{tenant_str}}{{prefix}}:*"
    await DragonflyService.delete_pattern(pattern)
    logger.info(f"Invalidated cache pattern: {{pattern}}")
"""
