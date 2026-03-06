"""AuditLog feature codegen for NIKAME.

Provides automated audit trails and context tracking.
"""

from __future__ import annotations
import logging
from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen

@register_codegen
class AuditLogCodegen(BaseCodegen):
    """Generates audit logging functionality."""

    NAME = "audit_log"
    DESCRIPTION = "Automated audit trail and history tracking"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        has_postgres = "postgres" in active_modules

        middleware_py = """\\"\\"\\"Audit Log Middleware.\\"\\"\\"
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
"""
        
        session_hook_py = """\\"\\"\\"Postgres Session Audit Wiring.\\"\\"\\"
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
import logging

logger = logging.getLogger("audit_db")

def wire_audit_to_session(session: AsyncSession):
    \\"\\"\\"Wires audit logging directly to the SQLAlchemy session.\\"\\"\\"
    @event.listens_for(session.sync_session, 'before_commit')
    def receive_before_commit(session):
        for obj in session.new:
            logger.info(f"AUDIT DB: Inserting {obj}")
        for obj in session.dirty:
            logger.info(f"AUDIT DB: Updating {obj}")
        for obj in session.deleted:
            logger.info(f"AUDIT DB: Deleting {obj}")
""" if has_postgres else ""

        files = [
            ("app/core/audit_middleware.py", middleware_py),
        ]
        
        if session_hook_py:
            files.append(("app/core/audit_db.py", session_hook_py))
            
        return files
