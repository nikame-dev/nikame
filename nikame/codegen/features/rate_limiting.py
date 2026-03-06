"""RateLimiting feature codegen for NIKAME.

Provides Redis/Dragonfly based API rate limiting.
"""

from __future__ import annotations
import logging
import time
from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen

@register_codegen
class RateLimitingCodegen(BaseCodegen):
    """Generates distributed rate limiting."""

    NAME = "rate_limiting"
    DESCRIPTION = "Redis/Dragonfly distributed rate limiting"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = ["redis"]

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        has_cache = any(m in ["dragonfly", "redis"] for m in active_modules)

        middleware_py = """\\"\\"\\"Rate limiting middleware.\\"\\"\\"
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.cache import cache
import time
import logging

logger = logging.getLogger("rate_limit")
RATE_LIMIT = 100 # requests per minute

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"
        
        current = await cache.get(key)
        if current and int(current) > RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(status_code=429, detail="Too Many Requests")
            
        pipe = cache.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        await pipe.execute()
        
        return await call_next(request)
""" if has_cache else ""

        if not middleware_py:
            return []

        return [
            ("app/core/rate_limit.py", middleware_py),
        ]
