"""Postgres Session Audit Wiring."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
import logging

logger = logging.getLogger("audit_db")

def wire_audit_to_session(session: AsyncSession):
    """Wires audit logging directly to the SQLAlchemy session."""
    @event.listens_for(session.sync_session, 'before_commit')
    def receive_before_commit(session):
        for obj in session.new:
            logger.info(f"AUDIT DB: Inserting {obj}")
        for obj in session.dirty:
            logger.info(f"AUDIT DB: Updating {obj}")
        for obj in session.deleted:
            logger.info(f"AUDIT DB: Deleting {obj}")
