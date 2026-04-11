import time
import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from app.core.settings import settings

# Redis connection pool
redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)

# LUA Script for atomic sliding window rate limiting
# KEYS[1] = Rate limit key (e.g., ip_user)
# ARGV[1] = Current timestamp
# ARGV[2] = Window size in seconds
# ARGV[3] = Max requests in window
LUA_SCRIPT = """
local window_start = tonumber(ARGV[1]) - tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', window_start)
local current_count = redis.call('ZCARD', KEYS[1])
if current_count < tonumber(ARGV[3]) then
    redis.call('ZADD', KEYS[1], ARGV[1], ARGV[1])
    redis.call('EXPIRE', KEYS[1], ARGV[2])
    return 0
else
    return 1
end
"""

async def sliding_window_limiter(request: Request, limit: int = 10, window: int = 60):
    key = f"rate_limit:{request.client.host}"
    now = time.time()
    
    # Execute Lua script
    is_limited = await redis_pool.eval(LUA_SCRIPT, 1, key, now, window, limit)
    
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
