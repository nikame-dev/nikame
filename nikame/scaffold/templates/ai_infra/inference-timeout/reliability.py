import asyncio
import logging
from typing import Any, Callable, Coroutine
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from fastapi import HTTPException

logger = logging.getLogger("app.ai_infra.reliability")

class InferenceTimeoutError(Exception):
    """Raised when inference exceeds the allotted time."""
    pass

def with_inference_reliability(
    timeout_seconds: float = 30.0,
    max_retries: int = 3
) -> Callable:
    """
    Decorator/Wrapper to add production-grade reliability to any inference call.
    Includes timeouts and exponential backoff retries.
    """
    
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((asyncio.TimeoutError, InferenceTimeoutError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        async def wrapper(*args, **kwargs):
            try:
                # Execution with hard timeout
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"Inference timed out after {timeout_seconds}s")
                raise InferenceTimeoutError(f"Model failed to respond within {timeout_seconds}s")
                
        return wrapper
        
    return decorator

async def safe_inference_call(
    call: Coroutine[Any, Any, Any],
    timeout: float = 30.0
) -> Any:
    """
    Functional alternative to the decorator for one-off calls.
    """
    try:
        return await asyncio.wait_for(call, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, 
            detail="Inference timed out. The model is currently overloaded."
        )
