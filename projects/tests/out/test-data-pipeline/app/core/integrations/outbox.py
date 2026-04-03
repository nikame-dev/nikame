import logging
from typing import List, Dict, Any
from sqlalchemy import select, update

from app.db.session import async_session
from app.models.outbox_event import OutboxEvent
from app.services.messaging import RedPandaService

logger = logging.getLogger(__name__)

async def write_to_outbox(session, topic: str, payload: dict):
    """Must be called inside an active SQLAlchemy Session transaction."""
    event = OutboxEvent(topic=topic, payload=payload)
    session.add(event)
    logger.debug("Stored event in transactional outbox.")

async def process_outbox_batch(batch_size: int = 50):
    """Scans for unprocessed events and publishes them to RedPanda."""
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

import asyncio
async def start_async_relay():
    """Inline relay loop since no Celery/Temporal workers are available."""
    while True:
        try:
            await process_outbox_batch()
            await asyncio.sleep(2) # Polling interval
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Outbox relay crashed: {e}")
            await asyncio.sleep(5)
