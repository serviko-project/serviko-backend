import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.bookings.models import Booking


class BasePromoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_usage_count(self, promo_id: uuid.UUID) -> int:
        q = select(func.count(Booking.id)).where(
            and_(
                Booking.promo_code_id == promo_id,
                Booking.status != "cancelled",
            ),
        )
        return (await self.db.execute(q)).scalar() or 0
