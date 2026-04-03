import json
import logging
from typing import Dict, Any

from app.services.messaging import RedPandaService

logger = logging.getLogger(__name__)

AUTH_TOPIC = "auth.lifecycle.events"

async def broadcast_auth_event(event_type: str, user_id: str, payload: Dict[str, Any]):
    """Broadcast user lifecycle events into the RedPanda cluster."""
    message = {
        "event_type": event_type,  # e.g., 'user_created', 'login', 'account_deleted'
        "user_id": user_id,
        "payload": payload
    }
    await RedPandaService.produce(AUTH_TOPIC, key=user_id, value=json.dumps(message))
    logger.debug(f"Broadcast auth event {event_type} for user {user_id}")
    # Prometheus metric: AUTH_EVENTS_PUBLISHED.inc()

# --- Example Auth Webhook Receiver Endpoint ---
# from fastapi import APIRouter
# router = APIRouter()
#
# @router.post("/webhooks/auth")
# async def handle_auth_webhook(webhook_data: dict):
#     """Hook into Keycloak/Authentik Outbound Webhooks."""
#     action = webhook_data.get("action")
#     uid = webhook_data.get("user_id")
#     await broadcast_auth_event(action, uid, webhook_data)
#     return {"status": "broadcasted"}
