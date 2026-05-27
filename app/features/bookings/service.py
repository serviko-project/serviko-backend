import uuid
from datetime import date, datetime, time, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ValidationException
from app.features.bookings.models import Booking
from app.features.bookings.base_service import BookingBaseService
from app.features.bookings.slot_service import SlotService
from app.features.bookings.booking_query_service import BookingQueryService
from app.features.bookings.booking_action_service import BookingActionService


class BookingService(BookingBaseService):
    BOOKING_EXPIRATION_HOURS = 3

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.slots = SlotService(db)
        self.queries = BookingQueryService(db, self.BOOKING_EXPIRATION_HOURS)
        self.actions = BookingActionService(db, self.queries)

    async def get_available_slots(
        self,
        provider_id: uuid.UUID,
        target_date: date,
        duration_hours: int,
    ) -> dict:
        return await self.slots.get_available_slots(provider_id, target_date, duration_hours)

    async def create_booking(
        self,
        customer_id: uuid.UUID,
        data: dict,
    ) -> Booking:
        service_id = data["service_id"]
        scheduled_date = data["scheduled_date"]
        start_time_str = data["start_time"]
        duration_hours = data["duration_hours"]

        # Parse start_time
        parts = start_time_str.split(":")
        start_time = time(int(parts[0]), int(parts[1]))
        end_hour = int(parts[0]) + duration_hours
        end_time = time(end_hour, int(parts[1]))

        # Verify service exists and get provider info
        svc = await self._get_provider_service(service_id)
        provider = svc.provider
        provider_id = svc.provider_id

        if provider.status != "approved" or provider.is_deleted:
            raise ValidationException("This provider is not currently accepting bookings")

        # Verify the customer is not booking their own service
        if provider.user_id == customer_id:
            raise ValidationException("You cannot book your own service")

        # Verify scheduled_date is today or future
        today = datetime.now(timezone.utc).date()
        if scheduled_date < today:
            raise ValidationException("Cannot book a past date")

        # Check provider availability for this day
        day_of_week = scheduled_date.weekday()
        availability = await self._get_day_availability(provider_id, day_of_week)

        if not availability or not availability.is_enabled:
            raise ValidationException("Provider is not available on this day")

        # Verify time is within provider's working hours
        if start_time < availability.start_time:
            raise ValidationException("Start time is before provider's working hours")

        if end_time > availability.end_time:
            raise ValidationException(
                f"Booking would exceed provider's working hours "
                f"(ends at {availability.end_time.strftime('%H:%M')})"
            )

        # Check for slot conflicts with existing bookings
        occupied_hours = await self.slots.get_occupied_hours(provider_id, scheduled_date)
        for h in range(start_time.hour, end_hour):
            if h in occupied_hours:
                raise ConflictException(
                    f"Time slot conflict: {h:02d}:00 is already booked"
                )

        # Snapshot price and calculate total
        base_price = svc.base_price_per_hour or 0.0
        original_price = base_price * duration_hours
        total_price = original_price
        discount_amount = 0.0
        promo_code_id = None

        promo_code_text = data.get("promo_code")
        if promo_code_text:
            from app.features.promo_codes.services import ValidationPromoService
            promo_service = ValidationPromoService(self.db)
            promo_res = await promo_service.validate_and_calculate(
                code=promo_code_text,
                provider_id=provider_id,
                customer_id=customer_id,
                subtotal=original_price,
            )
            promo_code_id = promo_res["promo_code_id"]
            discount_amount = promo_res["estimated_discount"]
            total_price = max(0.0, original_price - discount_amount)

        # Create booking
        booking = Booking(
            customer_id=customer_id,
            provider_id=provider_id,
            service_id=service_id,
            status="pending",
            scheduled_date=scheduled_date,
            start_time=start_time,
            duration_hours=duration_hours,
            end_time=end_time,
            base_price_per_hour=base_price,
            total_price=total_price,
            original_price=original_price,
            discount_amount=discount_amount,
            promo_code_id=promo_code_id,
            customer_latitude=data.get("customer_latitude"),
            customer_longitude=data.get("customer_longitude"),
            customer_address=data.get("customer_address"),
        )
        self.db.add(booking)
        await self.db.flush()
        await self.db.refresh(booking)

        return booking

    async def get_booking_detail(self, booking_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        return await self.queries.get_booking_detail(booking_id, user_id)

    async def list_customer_bookings(self, customer_id: uuid.UUID, status: str | None, page: int, limit: int) -> tuple[list[dict], int]:
        return await self.queries.list_customer_bookings(customer_id, status, page, limit)

    async def list_provider_bookings(self, provider_user_id: uuid.UUID, status: str | None, page: int, limit: int) -> tuple[list[dict], int]:
        return await self.queries.list_provider_bookings(provider_user_id, status, page, limit)

    async def review_booking(self, booking_id: uuid.UUID, provider_user_id: uuid.UUID, action: str, rejection_reason: str | None) -> dict:
        return await self.actions.review_booking(booking_id, provider_user_id, action, rejection_reason)

    async def cancel_booking(self, booking_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        return await self.actions.cancel_booking(booking_id, customer_id)

    async def complete_booking(self, booking_id: uuid.UUID, provider_user_id: uuid.UUID, completion_note: str | None) -> dict:
        return await self.actions.complete_booking(booking_id, provider_user_id, completion_note)
