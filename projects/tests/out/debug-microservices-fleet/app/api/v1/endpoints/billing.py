# NIKAME GENERATED — DO NOT EDIT DIRECTLY
import stripe
from typing import Optional
from fastapi import APIRouter, Header, Request, HTTPException
from config import settings

stripe.api_key = settings.STRIPE_API_KEY
WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.post("/checkout")
async def create_checkout_session(price_id: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"https://{settings.APP_NAME}.com/success",
            cancel_url=f"https://{settings.APP_NAME}.com/cancel",
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Dispatch a Celery task or update DB with the session
        print(f"Payment successful for session {session.id}")

    return {"status": "success"}