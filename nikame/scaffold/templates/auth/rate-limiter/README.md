# Redis Rate Limiter

Implements a sliding window rate limiter backed by Redis.

## Usage

Use the returned callable object as a FastAPI Dependency on your routers or individual endpoints.

```python
from fastapi import APIRouter, Depends
from app.auth.rate_limit import get_limiter

router = APIRouter()

# Limit to 5 requests per 60 seconds
@router.get("/heavy", dependencies=[Depends(get_limiter(requests=5, window_seconds=60))])
async def heavy_operation():
    return {"message": "Success"}
```

## Gotchas

* If Redis throws an exception (e.g. connection timeout), this component will currently **fail open** (it will allow the request through). This prevents your app from crashing if Redis goes down, but it breaks rate limiting. Adjust this via the `except redis.RedisError:` block.
* By default, it limits based on IP `request.client.host`. In a deployment environment running behind loadbalancers, this might be `127.0.0.1` unless you configure `ProxyHeadersMiddleware` or explicitly read from `X-Forwarded-For`.
