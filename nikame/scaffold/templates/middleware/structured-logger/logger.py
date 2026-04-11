import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# For advanced correlation you might import your get_request_id tool directly.
# from app.middleware.request_id import get_request_id

log = structlog.get_logger("app.middleware.requests")

class StructuredLoggerMiddleware(BaseHTTPMiddleware):
    """
    Automatically tracks and emits a clean JSON/structlog dictionary
    on every single incoming request and out-going response.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        
        # In a real app with RequestID middleware, we'd grab it like so:
        # request_id = get_request_id() or "none"
        
        structlog.contextvars.bind_contextvars(
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )
        
        log.info("request_started")
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            duration = time.perf_counter() - start_time
            log.info(
                "request_finished",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )
            return response
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            log.error(
                "request_failed",
                error=str(e),
                duration_ms=round(duration * 1000, 2)
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
