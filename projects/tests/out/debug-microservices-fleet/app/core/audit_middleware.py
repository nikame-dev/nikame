"""Audit Log Middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from uuid import uuid4

logger = logging.getLogger("audit_log")

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid4())
        logger.info(f"AUDIT [{req_id}] START: {request.method} {request.url.path}")

        response = await call_next(request)

        logger.info(f"AUDIT [{req_id}] END: {response.status_code}")
        return response
