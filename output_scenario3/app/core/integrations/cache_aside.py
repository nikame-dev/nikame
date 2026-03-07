import json
import logging
from functools import wraps
from typing import Any, Callable

from app.services.cache import DragonflyService

logger = logging.getLogger(__name__)

# Configured by MatrixEngine OptimizationProfile
DEFAULT_TTL = 3600

def cache_query(tenant_id: str = None, prefix: str, ttl: int = DEFAULT_TTL):
    """Decorator that implements the cache-aside pattern."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Construct key
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            
            tenant_str = f"{tenant_id}:" if tenant_id else ""
            cache_key = f"{tenant_str}{prefix}:{func.__name__}:{signature}"
            
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

async def invalidate_cache(tenant_id: str = None, prefix: str):
    """Invalidate all keys matching the prefix pattern."""
    tenant_str = f"{tenant_id}:" if tenant_id else ""
    pattern = f"{tenant_str}{prefix}:*"
    await DragonflyService.delete_pattern(pattern)
    logger.info(f"Invalidated cache pattern: {pattern}")
