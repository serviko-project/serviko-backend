import uuid
from datetime import date, datetime, time, timezone
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.features.bookings.models import Booking
from app.features.providers.models import (
    ProviderAvailability,
    ProviderProfile,
)


class SlotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_available_slots(
        self,
        provider_id: uuid.UUID,
        target_date: date,
        duration_hours: int,
    ) -> dict:
        # Verify provider exists and is approved
        await self._get_approved_provider(provider_id)

        # Get availability for the day of week
        day_of_week = target_date.weekday()
        availability = await self._get_day_availability(provider_id, day_of_week)

        if not availability or not availability.is_enabled:
            return {"date": target_date, "provider_id": provider_id, "slots": [], "max_duration_from_slot": {}}

        start_hour = availability.start_time.hour
        end_hour = availability.end_time.hour

        all_slots = [f"{hour:02d}:00" for hour in range(start_hour, end_hour)]
        occupied_hours = await self.get_occupied_hours(provider_id, target_date)

        now = datetime.now(timezone.utc)
        today = now.date()

        free_slots = []
        max_duration_map = {}

        for slot in all_slots:
            slot_hour = int(slot.split(":")[0])

            if target_date == today and slot_hour <= now.hour:
                continue

            if slot_hour in occupied_hours:
                continue

            free_slots.append(slot)

            max_dur = 0
            for h in range(slot_hour, end_hour):
                if h in occupied_hours:
                    break
                max_dur += 1
            max_duration_map[slot] = max_dur

        return {
            "date": target_date,
            "provider_id": provider_id,
            "slots": free_slots,
            "max_duration_from_slot": max_duration_map,
        }

    async def get_occupied_hours(
        self, provider_id: uuid.UUID, target_date: date
    ) -> set[int]:
        result = await self.db.execute(
            select(Booking.start_time, Booking.end_time).where(
                and_(
                    Booking.provider_id == provider_id,
                    Booking.scheduled_date == target_date,
                    Booking.status.in_(["pending", "confirmed"]),
                )
            )
        )
        rows = result.all()

        occupied = set()
        for row in rows:
            for h in range(row.start_time.hour, row.end_time.hour):
                occupied.add(h)
        return occupied

    async def _get_approved_provider(self, provider_id: uuid.UUID) -> ProviderProfile:
        result = await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise NotFoundException("Provider not found")
        if provider.status != "approved" or provider.is_deleted:
            raise ValidationException("Provider is not available")
        return provider

    async def _get_day_availability(
        self, provider_id: uuid.UUID, day_of_week: int
    ) -> ProviderAvailability | None:
        result = await self.db.execute(
            select(ProviderAvailability).where(
                and_(
                    ProviderAvailability.provider_id == provider_id,
                    ProviderAvailability.day_of_week == day_of_week,
                )
            )
        )
        return result.scalar_one_or_none()
