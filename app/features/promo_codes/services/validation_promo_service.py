import uuid

from sqlalchemy import select, and_, func

from app.core.exceptions import ValidationException
from app.features.bookings.models import Booking
from app.features.promo_codes.models import PromoCode
from app.features.promo_codes.services.base_service import BasePromoService


class ValidationPromoService(BasePromoService):
    async def validate_and_calculate(
        self,
        code: str,
        provider_id: uuid.UUID,
        customer_id: uuid.UUID,
        subtotal: float,
    ) -> dict:
        # Find promo code for this provider
        code_upper = code.strip().upper()
        result = await self.db.execute(
            select(PromoCode).where(
                and_(
                    PromoCode.provider_id == provider_id,
                    PromoCode.code == code_upper,
                ),
            ).with_for_update(),
        )
        promo = result.scalar_one_or_none()

        if not promo:
            raise ValidationException("Invalid promo code")

        if not promo.is_active:
            raise ValidationException("This promo code is no longer active")

        if promo.expires_at:
            from datetime import datetime, timezone
            if datetime.now(timezone.utc) > promo.expires_at.replace(tzinfo=timezone.utc):
                raise ValidationException("This promo code has expired")

        # Check min booking amount
        if promo.min_booking_amount and subtotal < promo.min_booking_amount:
            raise ValidationException(
                f"Minimum booking amount of ₹{promo.min_booking_amount:.0f} required",
            )

        # Check total usage limit
        if promo.max_uses:
            total_uses = await self._get_usage_count(promo.id)
            if total_uses >= promo.max_uses:
                raise ValidationException("This promo code has been fully redeemed")

        # Check per-customer usage
        customer_uses = await self._get_customer_usage_count(
            promo.id, customer_id,
        )
        if customer_uses >= promo.max_uses_per_customer:
            raise ValidationException("You have already used this promo code")

        # Calculate discount
        discount_amount = self._calculate_discount(promo, subtotal)

        return {
            "valid": True,
            "promo_code_id": promo.id,
            "code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "estimated_discount": discount_amount,
            "message": f"Promo applied! You save ₹{discount_amount:.2f}",
        }

    # -- Private helpers --

    def _calculate_discount(self, promo: PromoCode, subtotal: float) -> float:
        if promo.discount_type == "percentage":
            discount = round(subtotal * promo.discount_value / 100, 2)
            if promo.max_discount_amount and discount > promo.max_discount_amount:
                return float(promo.max_discount_amount)
            return discount
        return min(promo.discount_value, subtotal)

    async def _get_customer_usage_count(
        self, promo_id: uuid.UUID, customer_id: uuid.UUID,
    ) -> int:
        q = select(func.count(Booking.id)).where(
            and_(
                Booking.promo_code_id == promo_id,
                Booking.customer_id == customer_id,
                Booking.status != "cancelled",
            ),
        )
        return (await self.db.execute(q)).scalar() or 0
