import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

log = structlog.get_logger("app.middleware.latency")

# Requests taking longer than this threshold print a warning log
SLOW_REQUEST_THRESHOLD_SEC = 1.0

class LatencyTimerMiddleware(BaseHTTPMiddleware):
    """
    Times out how long the HTTP request takes across the ASGI stack,
    injects X-Process-Time into the response header, and warns on slow routes.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
        except Exception:
            # We still want to log latency on requests that fatally crash
            duration = time.perf_counter() - start_time
            if duration > SLOW_REQUEST_THRESHOLD_SEC:
                log.warning("slow_request_exception", method=request.method, path=request.url.path, duration_sec=duration)
            raise
            
        duration = time.perf_counter() - start_time
        
        # Inject standard metric header
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        
        if duration > SLOW_REQUEST_THRESHOLD_SEC:
            log.warning("slow_request", method=request.method, path=request.url.path, duration_sec=duration, status=response.status_code)
            
        return response
