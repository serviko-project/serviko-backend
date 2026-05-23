import uuid
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException, ValidationException
from app.features.bookings.models import Booking
from app.features.providers.models import ProviderService
from app.features.reviews.models import Review
from app.features.reviews.schemas import ReviewCreate


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_review(self, customer_id: uuid.UUID, data: ReviewCreate) -> Review:
        booking_result = await self.db.execute(
            select(Booking).where(Booking.id == data.booking_id)
        )
        booking = booking_result.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found")

        if booking.customer_id != customer_id:
            raise ForbiddenException(
                "You cannot review a booking that is not yours")

        if booking.status != "completed":
            raise ValidationException("You can only review completed bookings")

        existing_result = await self.db.execute(
            select(Review).where(Review.booking_id == data.booking_id)
        )
        if existing_result.scalar_one_or_none():
            raise ConflictException(
                "A review has already been submitted for this booking")

        review = Review(
            booking_id=booking.id,
            customer_id=customer_id,
            provider_id=booking.provider_id,
            provider_service_id=booking.service_id,
            rating=data.rating,
            comment=data.comment
        )
        self.db.add(review)
        await self.db.flush()

        stats_result = await self.db.execute(
            select(
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("total_reviews")
            ).where(Review.provider_service_id == booking.service_id)
        )
        stats = stats_result.one_or_none()

        avg_rating = float(
            stats.avg_rating) if stats and stats.avg_rating is not None else 0.0
        total_reviews = int(
            stats.total_reviews) if stats and stats.total_reviews is not None else 0

        ps_result = await self.db.execute(
            select(ProviderService).where(
                ProviderService.id == booking.service_id)
        )
        provider_service = ps_result.scalar_one_or_none()
        if provider_service:
            provider_service.rating = avg_rating
            provider_service.reviews_count = total_reviews
            self.db.add(provider_service)

        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def get_provider_reviews(
        self,
        provider_id: uuid.UUID,
        rating: int | None,
        page: int,
        limit: int,
    ) -> tuple[list[Review], int]:
        query = select(Review).where(Review.provider_id == provider_id)
        if rating is not None:
            query = query.where(Review.rating == rating)

        count_q = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_q) or 0

        query = (
            query.order_by(Review.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .options(
                joinedload(Review.customer),
                joinedload(Review.booking)
            )
        )
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        return reviews, total
