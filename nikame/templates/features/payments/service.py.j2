import stripe
from typing import Any, Dict, Optional

class StripeService:
    """Service to handle Stripe payments."""

    def __init__(self, api_key: str):
        stripe.api_key = api_key

    def create_checkout_session(
        self,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        price_id: str = "price_H5ggYyDqVvhvca",
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session."""
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email,
        )
        return session

    def fetch_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Fetch a subscription from Stripe."""
        return stripe.Subscription.retrieve(subscription_id)
