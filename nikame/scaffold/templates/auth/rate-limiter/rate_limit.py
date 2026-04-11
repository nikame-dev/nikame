import time
from typing import Callable
from fastapi import Request, Depends
import redis.asyncio as redis
from app.core.error_handlers import TooManyRequestsException

# Normally this comes from your Settings layer and is attached to app.state
# We use a global for the drop-in skeleton
REDIS_URL = "{{REDIS_URL}}" # e.g. "redis://localhost:6379/0"
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class RateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets.
    """
    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> bool:
        # Default identifier is the IP address. In real use, you'd likely want to 
        # extract the user_id if they are logged in, falling back to IP.
        identifier = "unknown"
        if request.client:
            identifier = request.client.host
        
        # Example lookup if using auth routines:
        # user = getattr(request.state, "user", None)
        # if user: identifier = f"user:{user.id}"

        key = f"rate_limit:{request.url.path}:{identifier}"
        now = time.time()
        window_start = now - self.window_seconds

        async with redis_client.pipeline() as pipe:
            try:
                # Remove score elements older than window_start
                pipe.zremrangebyscore(key, "-inf", window_start)
                
                # Count remainders
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(now): now})
                
                # Set TTL on the set to clean up idle limits
                pipe.expire(key, self.window_seconds)
                
                results = await pipe.execute()
            except redis.RedisError:
                # Fail open if Redis is down, to avoid cascade application failure
                return True

        current_count = results[1]
        
        if current_count >= self.requests:
            raise TooManyRequestsException(
                detail=f"Rate limit exceeded. Try again in {self.window_seconds}s",
                headers={"Retry-After": str(self.window_seconds)}
            )
            
        return True

def get_limiter(requests: int = 100, window_seconds: int = 60) -> RateLimiter:
    """Dependency factory helper."""
    return RateLimiter(requests, window_seconds)
