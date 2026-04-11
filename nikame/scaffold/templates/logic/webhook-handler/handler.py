import hmac
import hashlib
from typing import Optional
from fastapi import Request, HTTPException, status
from redis import Redis
from app.core.settings import settings

# For idempotency check
redis_client = Redis.from_url(settings.REDIS_URL)

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate webhook signature (generic example, adapt for Stripe/Razorpay)"""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

async def handle_webhook(request: Request, signature: Optional[str], event_id: Optional[str]):
    if not signature or not event_id:
        raise HTTPException(status_code=400, detail="Missing signature or event ID")

    # 1. Idempotency Check
    if redis_client.exists(f"webhook_event:{event_id}"):
        return {"status": "already_processed"}

    # 2. Verify Body Signature
    body = await request.body()
    if not verify_signature(body, signature, settings.WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 3. Mark as processing (with TTL)
    redis_client.setex(f"webhook_event:{event_id}", 86400, "processing")
    
    # 4. Process event (usually offload to Celery)
    # process_webook_event.delay(body.decode())
    
    return {"status": "success"}
