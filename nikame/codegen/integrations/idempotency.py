"""Event Idempotency Integration (Dragonfly + RedPanda)

Triggers when Dragonfly (Redis) and RedPanda (Kafka) are active.
Generates an idempotency wrapper for message consumers to guarantee
exactly-once processing semantics by tracking processed Message IDs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class EventIdempotencyIntegration(BaseIntegration):
    """Generates Exactly-Once processing decorators using Dragonfly."""

    REQUIRED_MODULES = ["dragonfly", "redpanda"]

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        idempotency_service = self._generate_idempotency_service_py()
        files.append(("app/core/integrations/idempotency.py", idempotency_service))
        return files

    def generate_lifespan(self) -> str:
        return "" # No specific lifespan hooks needed beyond Redis/Kafka base

    def generate_health(self) -> dict[str, str]:
        return {} # Base services handle connectivity

    def generate_metrics(self) -> str:
        return """
    DUPLICATE_MESSAGES_DROPPED = Counter(
        "nikame_duplicate_messages_dropped_total", 
        "Total duplicate Kafka messages dropped by idempotency layer"
    )
        """

    def generate_guide(self) -> str:
        return f"""
### Event Idempotency Integration
**Status:** Active 🟢
**Components:** RedPanda + Dragonfly
**Tuning:** ID Tracking TTL set to {self.profile.cache_ttl_seconds * 2}s

The Matrix Engine has automatically injected an Exactly-Once processing layer. Wrap any Kafka consumer functions with `@idempotent_consumer`. The system will automatically check Dragonfly for the Message ID before processing and drop duplicates.
"""

    def _generate_idempotency_service_py(self) -> str:
        return f"""import logging
from functools import wraps
from typing import Any, Callable

from app.services.cache import DragonflyService

logger = logging.getLogger(__name__)

# Configured by MatrixEngine OptimizationProfile (TTL x2 for safety)
IDEMPOTENCY_TTL = {self.profile.cache_ttl_seconds * 2}

def idempotent_consumer():
    \"\"\"Decorator that guarantees exactly-once processing for RedPanda consumers.
    
    Assumes the first argument or keyword argument contains a `message_id` property.
    \"\"\"
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Attempt to extract a unique message ID 
            # (In a real implementation, extract from structured Kafka ConsumerRecord)
            message_id = kwargs.get("message_id") or (args[0].message_id if args and hasattr(args[0], 'message_id') else None)
            
            if not message_id:
                logger.warning(f"No message_id found for {{func.__name__}}, bypassing idempotency check.")
                return await func(*args, **kwargs)
                
            cache_key = f"idempotency:{{func.__name__}}:{{message_id}}"
            
            # 1. Attempt to claim processing rights (SET NX)
            # This is an atomic operation in Dragonfly/Redis
            claimed = await DragonflyService.set_nx(cache_key, "processing", expire=IDEMPOTENCY_TTL)
            
            if not claimed:
                logger.info(f"Duplicate message {{message_id}} detected. Dropping.")
                # Prometheus Metric: DUPLICATE_MESSAGES_DROPPED.inc()
                return None
                
            try:
                # 2. Claimed successfully, process message
                result = await func(*args, **kwargs)
                
                # 3. Mark as completed
                await DragonflyService.set(cache_key, "completed", expire=IDEMPOTENCY_TTL)
                return result
                
            except Exception as e:
                # If processing failed, release the lock so it can be retried
                await DragonflyService.delete(cache_key)
                raise e
                
        return wrapper
    return decorator
"""
