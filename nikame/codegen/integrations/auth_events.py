"""Auth Event Bus Integration

Triggers when Keycloak/Authentik and RedPanda are active.
Hooks authentication webhooks/events into a Kafka topic to trigger
downstream actions (e.g. welcoming new users, syncing CRM, wiping data
on account deletion) across microservices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class AuthEventBusIntegration(BaseIntegration):
    """Generates the centralized auth event propagation bus."""

    REQUIRED_MODULES = ["redpanda"]
    REQUIRED_FEATURES = ["auth"]

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        event_bus = self._generate_auth_event_bus_py()
        files.append(("app/core/integrations/auth_event_bus.py", event_bus))
        return files

    def generate_lifespan(self) -> str:
        return ""

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return """
    AUTH_EVENTS_PUBLISHED = Counter("nikame_auth_events_published_total", "Total auth lifecycle events broadcast")
        """

    def generate_guide(self) -> str:
        return """
### Auth Event Bus
**Status:** Active 🟢
**Components:** Auth + RedPanda

Because your stack contains both an Authentication Provider and an Event Bus, Keycloak/Authentik lifecycle events (Sign Up, Login, Delete, Password Reset) are automatically caught and broadcast to the `auth.lifecycle.events` RedPanda topic. 

Any other microservice or worker can subscribe to this topic to react to user milestones (e.g. creating default records for new users or deleting PII upon account closure).
"""

    def _generate_auth_event_bus_py(self) -> str:
        return """import json
import logging
from typing import Dict, Any

from app.services.messaging import RedPandaService

logger = logging.getLogger(__name__)

AUTH_TOPIC = "auth.lifecycle.events"

async def broadcast_auth_event(event_type: str, user_id: str, payload: Dict[str, Any]):
    \"\"\"Broadcast user lifecycle events into the RedPanda cluster.\"\"\"
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
#     \"\"\"Hook into Keycloak/Authentik Outbound Webhooks.\"\"\"
#     action = webhook_data.get("action")
#     uid = webhook_data.get("user_id")
#     await broadcast_auth_event(action, uid, webhook_data)
#     return {"status": "broadcasted"}
"""
