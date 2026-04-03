import logging
from functools import wraps
from typing import Any, Callable

from app.services.cache import DragonflyService

logger = logging.getLogger(__name__)

# Configured by MatrixEngine OptimizationProfile (TTL x2 for safety)
IDEMPOTENCY_TTL = 7200

def idempotent_consumer():
    """Decorator that guarantees exactly-once processing for RedPanda consumers.
    
    Assumes the first argument or keyword argument contains a `message_id` property.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Attempt to extract a unique message ID 
            # (In a real implementation, extract from structured Kafka ConsumerRecord)
            message_id = kwargs.get("message_id") or (args[0].message_id if args and hasattr(args[0], 'message_id') else None)
            
            if not message_id:
                logger.warning(f"No message_id found for {func.__name__}, bypassing idempotency check.")
                return await func(*args, **kwargs)
                
            cache_key = f"idempotency:{func.__name__}:{message_id}"
            
            # 1. Attempt to claim processing rights (SET NX)
            # This is an atomic operation in Dragonfly/Redis
            claimed = await DragonflyService.set_nx(cache_key, "processing", expire=IDEMPOTENCY_TTL)
            
            if not claimed:
                logger.info(f"Duplicate message {message_id} detected. Dropping.")
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
