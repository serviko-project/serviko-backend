import uuid
from datetime import time
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException
from app.features.bookings.models import Booking
from app.features.providers.models import (
    ProviderAvailability,
    ProviderProfile,
    ProviderService,
)


class BookingBaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_provider_service(self, service_id: uuid.UUID) -> ProviderService:
        result = await self.db.execute(
            select(ProviderService)
            .where(ProviderService.id == service_id)
            .options(
                joinedload(ProviderService.provider).joinedload(
                    ProviderProfile.user),
                joinedload(ProviderService.category),
            )
        )
        service = result.scalar_one_or_none()
        if not service:
            raise NotFoundException("Service not found")
        return service

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
