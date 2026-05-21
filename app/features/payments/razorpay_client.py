import hmac
import hashlib

import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationException


class RazorpayClient:
    base_url = "https://api.razorpay.com/v1"

    def __init__(self):
        self.settings = get_settings()

    @property
    def key_id(self) -> str:
        return self.settings.RAZORPAY_KEY_ID

    def _ensure_configured(self) -> None:
        if not self.settings.RAZORPAY_KEY_ID or not self.settings.RAZORPAY_KEY_SECRET:
            raise ValidationException("Razorpay test keys are not configured")

    async def create_order(
        self,
        *,
        amount_paise: int,
        currency: str,
        receipt: str,
        notes: dict[str, str],
    ) -> dict:
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/orders",
                auth=(self.settings.RAZORPAY_KEY_ID,
                      self.settings.RAZORPAY_KEY_SECRET),
                json={
                    "amount": amount_paise,
                    "currency": currency,
                    "receipt": receipt,
                    "notes": notes,
                },
            )

        if response.status_code >= 400:
            raise ValidationException("Unable to create Razorpay order")
        return response.json()

    async def refund_payment(self, *, payment_id: str, amount_paise: int) -> dict:
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/payments/{payment_id}/refund",
                auth=(self.settings.RAZORPAY_KEY_ID,
                      self.settings.RAZORPAY_KEY_SECRET),
                json={"amount": amount_paise},
            )

        if response.status_code >= 400:
            raise ValidationException("Unable to refund Razorpay payment")
        return response.json()

    def verify_payment_signature(
        self,
        *,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        self._ensure_configured()
        payload = f"{order_id}|{payment_id}".encode()
        expected = hmac.new(
            self.settings.RAZORPAY_KEY_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        if not self.settings.RAZORPAY_WEBHOOK_SECRET:
            raise ValidationException(
                "Razorpay webhook secret is not configured")
        expected = hmac.new(
            self.settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
