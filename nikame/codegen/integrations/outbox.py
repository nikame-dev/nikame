"""Outbox Pattern Integration (Postgres + RedPanda)

Triggers when Postgres and RedPanda are active.
Generates a reliable outbox message relay to solve the dual-write problem.
Ensures local database transactions and Kafka message emissions are 
atomically linked via an 'outbox' database table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class OutboxPatternIntegration(BaseIntegration):
    """Generates the transactional outbox pattern."""

    REQUIRED_MODULES = ["postgres", "redpanda"]
    DEPENDS_ON = ["BrokerAutoWiringIntegration"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_celery = "celery" in self.active_modules
        self.use_temporal = "temporal" in self.active_modules

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        outbox_model = self._generate_outbox_model_py()
        files.append(("app/models/outbox_event.py", outbox_model))

        outbox_service = self._generate_outbox_service_py()
        files.append(("app/core/integrations/outbox.py", outbox_service))
        return files

    def generate_lifespan(self) -> str:
        if not self.use_celery and not self.use_temporal:
            return """
    # --- Outbox Pattern Startup ---
    # Because no worker is active, start a background asyncio task for the outbox relay
    from app.core.integrations.outbox import start_async_relay
    import asyncio
    asyncio.create_task(start_async_relay())
            """
        return ""

    def generate_health(self) -> dict[str, str]:
        return {
            "outbox_backlog_size": "await get_pending_outbox_count()"
        }

    def generate_metrics(self) -> str:
        return """
    OUTBOX_MESSAGES_PUBLISHED = Counter(
        "nikame_outbox_messages_published_total", 
        "Total events successfully relayed from db outbox to Kafka"
    )
        """

    def generate_guide(self) -> str:
        return """
### Transactional Outbox Pattern
**Status:** Active 🟢
**Components:** Postgres + RedPanda

When building distributed systems, updating a database and publishing an event (dual-write) can lead to inconsistencies if the system crashes midway. The Matrix Engine has added the Transactional Outbox Pattern to fix this:

1. In your `async_session`, save business models AND `OutboxEvent` models in the exact same transaction.
2. A background process sweeps the Outbox table for unpublished events and guarantees delivery to RedPanda 'at-least-once'.
"""

    def _generate_outbox_model_py(self) -> str:
        return """from sqlalchemy import Column, String, JSON, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

    def _generate_outbox_service_py(self) -> str:
        template = """import logging
from typing import List, Dict, Any
from sqlalchemy import select, update

from app.db.session import async_session
from app.models.outbox_event import OutboxEvent
from app.services.messaging import RedPandaService

logger = logging.getLogger(__name__)

async def write_to_outbox(session, topic: str, payload: dict):
    \"\"\"Must be called inside an active SQLAlchemy Session transaction.\"\"\"
    event = OutboxEvent(topic=topic, payload=payload)
    session.add(event)
    logger.debug("Stored event in transactional outbox.")

async def process_outbox_batch(batch_size: int = 50):
    \"\"\"Scans for unprocessed events and publishes them to RedPanda.\"\"\"
    async with async_session() as db:
        # 1. Fetch pending
        stmt = select(OutboxEvent).where(OutboxEvent.processed == False).limit(batch_size).with_for_update(skip_locked=True)
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        if not events:
            return
            
        # 2. Publish and mark processed
        for event in events:
            try:
                import json
                await RedPandaService.produce(event.topic, key=event.id, value=json.dumps(event.payload))
                event.processed = True
                # Prometheus Metric: OUTBOX_MESSAGES_PUBLISHED.inc()
                logger.debug(f"Relayed outbox event {event.id} to {event.topic}")
            except Exception as e:
                logger.error(f"Failed to relay outbox event {event.id}: {e}")
                # We skip this one, transaction won't commit it as processed.
                
        # 3. Commit the 'processed=True' state
        await db.commit()
"""
        if not self.use_celery and not self.use_temporal:
            template += """
import asyncio
async def start_async_relay():
    \"\"\"Inline relay loop since no Celery/Temporal workers are available.\"\"\"
    while True:
        try:
            await process_outbox_batch()
            await asyncio.sleep(2) # Polling interval
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Outbox relay crashed: {e}")
            await asyncio.sleep(5)
"""
        return template
