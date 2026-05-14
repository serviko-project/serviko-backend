import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, ValidationException
from app.features.bookings.booking_query_service import BookingQueryService
from app.features.bookings.mappers import map_booking_to_detail_dict


class BookingActionService:
    def __init__(self, db: AsyncSession, query_service: BookingQueryService):
        self.db = db
        self.query_service = query_service

    async def review_booking(
        self,
        booking_id: uuid.UUID,
        provider_user_id: uuid.UUID,
        action: str,
        rejection_reason: str | None,
    ) -> dict:
        booking = await self.query_service._get_booking_with_joins(booking_id)

        if booking.provider.user_id != provider_user_id:
            raise ForbiddenException("You can only review your own bookings")

        if booking.status == "pending":
            expiration_limit = datetime.now(timezone.utc) - timedelta(
                hours=self.query_service.expiration_hours
            )
            if booking.created_at < expiration_limit:
                booking.status = "expired"
                await self.db.flush()
                raise ValidationException("This booking request has expired")

        if booking.status != "pending":
            raise ValidationException(
                f"Cannot review a booking with status '{booking.status}'"
            )

        now = datetime.now(timezone.utc)

        if action == "confirm":
            booking.status = "confirmed"
            booking.confirmed_at = now
        elif action == "reject":
            if not rejection_reason or not rejection_reason.strip():
                raise ValidationException("Rejection reason is required")
            booking.status = "rejected"
            booking.rejection_reason = rejection_reason.strip()
            booking.rejected_at = now

        await self.db.flush()
        await self.db.refresh(booking)

        return map_booking_to_detail_dict(booking)

    async def cancel_booking(
        self,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> dict:
        booking = await self.query_service._get_booking_with_joins(booking_id)

        if booking.customer_id != customer_id:
            raise ForbiddenException("You can only cancel your own bookings")

        if booking.status not in ("pending", "confirmed"):
            raise ValidationException(
                f"Cannot cancel a booking with status '{booking.status}'"
            )

        booking.status = "cancelled"
        booking.cancelled_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(booking)

        return map_booking_to_detail_dict(booking)
