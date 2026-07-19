import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_checkout_session(booking_ref: str, amount: float, customer_email: str, success_url: str, cancel_url: str):
        # Default to test key if not configured in settings
        if not settings.STRIPE_SECRET_KEY:
            # We can return a fake session object/URL for development
            return {
                "id": f"fake_session_{booking_ref}",
                "url": f"{success_url}?session_id=fake_session_{booking_ref}"
            }
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "gbp",
                            "product_data": {
                                "name": f"Taxi Booking Ref: {booking_ref}",
                            },
                            "unit_amount": int(amount * 100), # Stripe expects pence
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                customer_email=customer_email,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "booking_reference": booking_ref
                }
            )
            return session
        except Exception as e:
            raise RuntimeError(f"Stripe Session creation failed: {e}")

    @staticmethod
    def verify_webhook(payload: str, sig_header: str) -> dict:
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
            # Fake webhook validation for development
            import json
            try:
                event = json.loads(payload)
                return event
            except Exception:
                return {}
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f"Invalid signature: {e}")
        except Exception as e:
            raise ValueError(f"Webhook parsing failed: {e}")
