import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timedelta, timezone

from app.core.exceptions import ForbiddenException, NotFoundException
from app.features.bookings.models import Booking
from app.features.providers.models import ProviderProfile, ProviderService
from app.features.bookings.mappers import (
    map_booking_to_detail_dict,
    map_booking_to_list_item_dict,
)


class BookingQueryService:
    def __init__(self, db: AsyncSession, expiration_hours: int):
        self.db = db
        self.expiration_hours = expiration_hours

    async def get_booking_detail(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        booking = await self._get_booking_with_joins(booking_id)

        if (
            booking.customer_id != user_id
            and booking.provider.user_id != user_id
        ):
            raise ForbiddenException("You don't have access to this booking")

        return map_booking_to_detail_dict(booking)

    async def list_customer_bookings(
        self,
        customer_id: uuid.UUID,
        status: str | None,
        page: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        await self.handle_pending_expirations(customer_id=customer_id)

        query = (
            select(Booking)
            .where(Booking.customer_id == customer_id)
            .order_by(Booking.created_at.desc())
        )

        if status:
            query = query.where(Booking.status == status)

        count_q = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_q) or 0

        query = (
            query.offset((page - 1) * limit)
            .limit(limit)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.provider).joinedload(ProviderProfile.user),
                joinedload(Booking.service).joinedload(
                    ProviderService.category),
                selectinload(Booking.payments),
            )
        )

        result = await self.db.execute(query)
        bookings = result.scalars().all()

        return [map_booking_to_list_item_dict(b) for b in bookings], total

    async def list_provider_bookings(
        self,
        provider_user_id: uuid.UUID,
        status: str | None,
        page: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        await self.handle_pending_expirations(provider_user_id=provider_user_id)

        query = (
            select(Booking)
            .join(ProviderProfile)
            .where(ProviderProfile.user_id == provider_user_id)
            .order_by(Booking.created_at.desc())
        )

        if status:
            query = query.where(Booking.status == status)

        count_q = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_q) or 0

        query = (
            query.offset((page - 1) * limit)
            .limit(limit)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.provider).joinedload(ProviderProfile.user),
                joinedload(Booking.service).joinedload(
                    ProviderService.category),
                selectinload(Booking.payments),
            )
        )

        result = await self.db.execute(query)
        bookings = result.scalars().all()

        return [map_booking_to_list_item_dict(b) for b in bookings], total

    async def handle_pending_expirations(
        self,
        provider_user_id: uuid.UUID = None,
        customer_id: uuid.UUID = None,
    ):
        expiration_limit = datetime.now(timezone.utc) - timedelta(
            hours=self.expiration_hours
        )

        stmt = (
            update(Booking)
            .where(
                Booking.status == "pending",
                Booking.created_at < expiration_limit,
            )
            .values(status="expired")
        )

        if provider_user_id:
            subq = (
                select(Booking.id)
                .join(ProviderProfile)
                .where(
                    Booking.status == "pending",
                    Booking.created_at < expiration_limit,
                    ProviderProfile.user_id == provider_user_id,
                )
            )
            stmt = (
                update(Booking)
                .where(Booking.id.in_(subq))
                .values(status="expired")
            )
        elif customer_id:
            stmt = stmt.where(Booking.customer_id == customer_id)

        await self.db.execute(stmt)
        await self.db.flush()

    async def _get_booking_with_joins(self, booking_id: uuid.UUID) -> Booking:
        result = await self.db.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.provider).joinedload(ProviderProfile.user),
                joinedload(Booking.service).joinedload(
                    ProviderService.category),
                selectinload(Booking.payments),
            )
        )
        booking = result.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found")
        return booking
