"""Webhook reception and routing."""
from fastapi import APIRouter, Request, HTTPException
import logging
from core.messaging import kafka_service


logger = logging.getLogger("webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
has_messaging = True

@router.post("/{source}")
async def receive_webhook(source: str, request: Request):
    """Generic webhook reception endpoint."""
    try:
        payload = await request.json()
        logger.info(f"Received webhook from {source}")

        if has_messaging:
            await kafka_service.send_message("webhook.events", {"source": source, "payload": payload})

        return {"status": "received", "source": source}
    except Exception as e:
        logger.error(f"Webhook processing error for {source}: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
