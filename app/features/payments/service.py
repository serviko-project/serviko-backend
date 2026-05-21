import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import get_settings
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.features.bookings.models import Booking
from app.features.payments.models import Payment
from app.features.payments.razorpay_client import RazorpayClient


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.razorpay = RazorpayClient()

    async def create_order(
        self,
        *,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> dict:
        booking = await self._get_booking(booking_id)

        if booking.customer_id != customer_id:
            raise ForbiddenException("You can only pay for your own bookings")
        if booking.status != "confirmed":
            raise ValidationException(
                "Payment is allowed only after provider acceptance")

        existing = self._latest_payment(booking)
        if existing and existing.status == "paid":
            raise ValidationException("This booking is already paid")
        if existing and existing.status == "created" and existing.razorpay_order_id:
            return self._map_order_response(existing, booking)

        amount_paise = self._to_paise(booking.total_price)
        order = await self.razorpay.create_order(
            amount_paise=amount_paise,
            currency=self.settings.RAZORPAY_CURRENCY,
            receipt=f"booking_{str(booking.id)[:24]}",
            notes={
                "booking_id": str(booking.id),
                "customer_id": str(booking.customer_id),
                "provider_id": str(booking.provider_id),
            },
        )

        payment = Payment(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            provider_id=booking.provider_id,
            amount=booking.total_price,
            currency=self.settings.RAZORPAY_CURRENCY,
            status="created",
            razorpay_order_id=order["id"],
            razorpay_status=order.get("status"),
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return self._map_order_response(payment, booking)

    async def verify_payment(
        self,
        *,
        customer_id: uuid.UUID,
        booking_id: uuid.UUID,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> dict:
        booking = await self._get_booking(booking_id)
        if booking.customer_id != customer_id:
            raise ForbiddenException("You can only verify your own payments")

        payment = await self._get_payment_by_order(razorpay_order_id)
        if payment.booking_id != booking.id:
            raise ValidationException(
                "Payment order does not belong to this booking")

        is_valid = self.razorpay.verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
        )
        if not is_valid:
            payment.status = "failed"
            payment.failure_reason = "Invalid Razorpay signature"
            await self.db.flush()
            raise ValidationException("Invalid Razorpay payment signature")

        payment.status = "paid"
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.razorpay_status = "paid"
        payment.failure_reason = None
        payment.paid_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(payment)
        return self._map_payment_response(payment)

    async def get_booking_payment(
        self,
        *,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        booking = await self._get_booking(booking_id)
        if booking.customer_id != user_id and booking.provider.user_id != user_id:
            raise ForbiddenException("You don't have access to this payment")

        payment = self._latest_payment(booking)
        if not payment:
            raise NotFoundException("Payment not found")
        return self._map_payment_response(payment)

    async def refund_paid_booking(self, booking: Booking) -> Payment | None:
        payment = self._latest_payment(booking)
        if not payment or payment.status != "paid":
            return payment
        if not payment.razorpay_payment_id:
            payment.status = "refund_pending"
            payment.failure_reason = "Missing Razorpay payment id for refund"
            await self.db.flush()
            return payment

        payment.status = "refund_pending"
        await self.db.flush()

        amount_paise = self._to_paise(payment.amount)
        await self.razorpay.refund_payment(
            payment_id=payment.razorpay_payment_id,
            amount_paise=amount_paise,
        )

        payment.status = "refunded"
        payment.refunded_at = datetime.now(timezone.utc)
        payment.razorpay_status = "refunded"
        await self.db.flush()
        return payment

    async def handle_webhook(self, *, payload: dict) -> None:
        event = payload.get("event")
        if event not in {"order.paid", "payment.captured"}:
            return

        entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        order_id = entity.get("order_id")
        payment_id = entity.get("id")
        if not order_id or not payment_id:
            return

        payment = await self._get_payment_by_order(order_id)
        if payment.status == "paid":
            return
        payment.status = "paid"
        payment.razorpay_payment_id = payment_id
        payment.razorpay_status = entity.get("status") or "captured"
        payment.paid_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def _get_booking(self, booking_id: uuid.UUID) -> Booking:
        result = await self.db.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.provider),
                selectinload(Booking.payments),
            )
        )
        booking = result.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found")
        return booking

    async def _get_payment_by_order(self, razorpay_order_id: str) -> Payment:
        result = await self.db.execute(
            select(Payment).where(
                Payment.razorpay_order_id == razorpay_order_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment order not found")
        return payment

    def _latest_payment(self, booking: Booking) -> Payment | None:
        payments = sorted(booking.payments,
                          key=lambda p: p.created_at, reverse=True)
        return payments[0] if payments else None

    def _map_order_response(self, payment: Payment, booking: Booking) -> dict:
        customer = booking.customer
        return {
            "payment_id": payment.id,
            "booking_id": booking.id,
            "razorpay_key_id": self.razorpay.key_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "amount": self._to_paise(payment.amount),
            "amount_rupees": payment.amount,
            "currency": payment.currency,
            "customer_name": customer.full_name if customer else None,
            "customer_email": customer.email if customer else None,
            "customer_phone": customer.phone_number if customer else None,
            "description": f"Serviko booking payment for {booking.scheduled_date}",
        }

    def _map_payment_response(self, payment: Payment) -> dict:
        return {
            "id": payment.id,
            "booking_id": payment.booking_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "gateway": payment.gateway,
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "paid_at": payment.paid_at,
            "refunded_at": payment.refunded_at,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }

    def _to_paise(self, amount_rupees: float) -> int:
        return int(round(amount_rupees * 100))
