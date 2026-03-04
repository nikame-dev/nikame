from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any
import stripe
import os

from .service import StripeService
from ..auth import dependencies, models as auth_models

router = APIRouter()

def get_stripe_service() -> StripeService:
    return StripeService(api_key=os.getenv("STRIPE_API_KEY", ""))

@router.post("/create-checkout-session")
async def create_checkout_session(
    price_id: str,
    current_user: auth_models.User = Depends(dependencies.get_current_active_user),
    service: StripeService = Depends(get_stripe_service),
) -> Any:
    """Create a Stripe checkout session for a subscription."""
    try:
        session = service.create_checkout_session(
            success_url=f"http://localhost:8000/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"http://localhost:8000/cancel",
            customer_email=current_user.email,
            price_id=price_id,
        )
        return {"session_id": session.id, "checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request) -> Any:
    """Stripe webhook handler."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Handle successful payment
        pass

    return {"status": "success"}
