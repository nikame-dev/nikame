import asyncio
from typing import Optional
from fastapi import Request, HTTPException

# Default to 1 concurrent request if not specified
DEFAULT_MAX_CONCURRENT = 1

class InferenceSemaphore:
    """
    Global semaphore to limit concurrent access to the GPU.
    """
    def __init__(self, count: int = DEFAULT_MAX_CONCURRENT):
        self.semaphore = asyncio.Semaphore(count)
        self.max_count = count

    async def acquire(self):
        # We could add a timeout here with asyncio.wait_for 
        # to return a 503 instead of hanging indefinitely
        await self.semaphore.acquire()

    def release(self):
        self.semaphore.release()

# Global instance for the app
inference_limiter = InferenceSemaphore(int("{{MAX_CONCURRENT_INFERENCE}}" or DEFAULT_MAX_CONCURRENT))

async def get_gpu_lock(request: Request):
    """
    FastAPI dependency to protect an endpoint with the GPU semaphore.
    Usage: Depends(get_gpu_lock)
    """
    try:
        # Wait until a spot opens up in the GPU queue
        # In a high-traffic app, you might want to wrap this in a timeout
        await inference_limiter.acquire()
        yield
    finally:
        # Always release, even if the request crashes
        inference_limiter.release()
