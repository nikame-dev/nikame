import uuid
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import contextvars

# Context string to access the request ID from anywhere within the request cycle
request_id_context_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request has an X-Request-ID.
    If the client sends one, we reuse it (for distributed tracing across services).
    If they don't, we generate a fresh UUID.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())
            
        # Bind into contextvar so logs deep in the application can read it
        token = request_id_context_var.set(req_id)
        
        try:
            response = await call_next(request)
            # Guarantee the response includes the tracking ID back to the client
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_context_var.reset(token)

def get_request_id() -> Optional[str]:
    """Helper to safely fetch the current contextual Request ID"""
    return request_id_context_var.get()
