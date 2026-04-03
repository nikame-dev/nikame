"""Webhook feature codegen for NIKAME.

Provides outgoing and incoming webhooks orchestration.
"""

from __future__ import annotations
import logging
from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen

@register_codegen
class WebhookCodegen(BaseCodegen):
    """Generates webhook handling code."""

    NAME = "webhooks"
    DESCRIPTION = "Incoming/Outgoing webhooks orchestration"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = []

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        has_messaging = any(m in ["redpanda", "kafka"] for m in active_modules)

        kafka_import = "from core.messaging import kafka_service\n" if has_messaging else ""
        kafka_publish = """
        if has_messaging:
            await kafka_service.send_message("webhook.events", {"source": source, "payload": payload})
""" if has_messaging else ""

        router_py = f'''"""Webhook reception and routing."""
from fastapi import APIRouter, Request, HTTPException
import logging
{kafka_import}

logger = logging.getLogger("webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
has_messaging = {'True' if has_messaging else 'False'}

@router.post("/{{source}}")
async def receive_webhook(source: str, request: Request):
    """Generic webhook reception endpoint."""
    try:
        payload = await request.json()
        logger.info(f"Received webhook from {{source}}")
{kafka_publish}
        return {{"status": "received", "source": source}}
    except Exception as e:
        logger.error(f"Webhook processing error for {{source}}: {{e}}")
        raise HTTPException(status_code=400, detail="Invalid payload")
'''

        return [
            ("app/api/webhooks/router.py", router_py),
        ]
