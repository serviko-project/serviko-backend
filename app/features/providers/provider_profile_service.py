import uuid

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.storage import StorageBucket, delete_file, upload_file
from app.features.providers.base_service import ProviderBaseService
from app.features.providers.models import ProviderProfile
from app.features.providers.schemas import ProviderDetailsUpdate, ServiceCategoryInput, AvailabilitySlotCreate
from app.utils.enums import ProviderStatus



class ProviderProfileService(ProviderBaseService):
    # Update basic provider details
    async def update_details(
        self, user_id: uuid.UUID, data: ProviderDetailsUpdate
    ) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider profile found")

        if profile.status != ProviderStatus.APPROVED.value:
            raise ForbiddenException(
                "Only approved providers can edit their details"
            )

        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return profile

        for field, value in update_fields.items():
            setattr(profile, field, value)

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    # Upload banner image
    async def upload_banner(
        self, user_id: uuid.UUID, file_bytes: bytes, content_type: str
    ) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider profile found")

        if profile.status != ProviderStatus.APPROVED.value:
            raise ForbiddenException(
                "Only approved providers can upload a banner"
            )

        # Delete old banner if exists
        if profile.banner_image_url:
            delete_file(StorageBucket.PROVIDER_BANNERS,
                        profile.banner_image_url)

        # Upload new banner
        public_url = upload_file(
            bucket=StorageBucket.PROVIDER_BANNERS,
            folder=str(profile.id),
            file_bytes=file_bytes,
            content_type=content_type,
        )

        profile.banner_image_url = public_url
        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    # Delete banner image
    async def delete_banner(self, user_id: uuid.UUID) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider profile found")

        if profile.banner_image_url:
            delete_file(StorageBucket.PROVIDER_BANNERS,
                        profile.banner_image_url)

        profile.banner_image_url = None
        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    # Get provider dashboard statistics
    async def get_dashboard_stats(self, user_id: uuid.UUID) -> dict:
        from datetime import date
        from sqlalchemy import select, func
        from sqlalchemy.orm import joinedload, selectinload
        from app.features.bookings.models import Booking
        from app.features.providers.models import ProviderService
        from app.features.bookings.mappers import map_booking_to_list_item_dict

        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider profile found")

        provider_id = profile.id
        today = date.today()

        # Today's Earnings
        earnings_stmt = select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
            Booking.provider_id == provider_id,
            Booking.status == "completed",
            func.date(Booking.completed_at) == today
        )
        earnings_res = await self.db.execute(earnings_stmt)
        today_earnings = float(earnings_res.scalar() or 0.0)

        # Active Jobs Count (Count of confirmed bookings scheduled for today)
        active_stmt = select(func.count(Booking.id)).where(
            Booking.provider_id == provider_id,
            Booking.status == "confirmed",
            Booking.scheduled_date == today
        )
        active_res = await self.db.execute(active_stmt)
        active_jobs_count = int(active_res.scalar() or 0)

        # New Requests Count (Count of pending bookings)
        pending_stmt = select(func.count(Booking.id)).where(
            Booking.provider_id == provider_id,
            Booking.status == "pending"
        )
        pending_res = await self.db.execute(pending_stmt)
        new_requests_count = int(pending_res.scalar() or 0)

        # Average Rating (Computed from provider services ratings)
        rating_stmt = select(func.coalesce(func.avg(ProviderService.rating), 0.0)).where(
            ProviderService.provider_id == provider_id,
            ProviderService.reviews_count > 0
        )
        rating_res = await self.db.execute(rating_stmt)
        rating = float(rating_res.scalar() or 0.0)

        # Next Job (Upcoming confirmed booking today/future)
        next_job_stmt = (
            select(Booking)
            .where(
                Booking.provider_id == provider_id,
                Booking.status == "confirmed",
                Booking.scheduled_date >= today
            )
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.provider).joinedload(ProviderProfile.user),
                joinedload(Booking.service).joinedload(
                    ProviderService.category),
                selectinload(Booking.payments),
                joinedload(Booking.promo_code),
            )
            .order_by(Booking.scheduled_date.asc(), Booking.start_time.asc())
            .limit(1)
        )
        next_job_res = await self.db.execute(next_job_stmt)
        next_job_model = next_job_res.scalar_one_or_none()

        next_job_data = None
        if next_job_model:
            next_job_data = map_booking_to_list_item_dict(next_job_model)

        return {
            "today_earnings": today_earnings,
            "active_jobs_count": active_jobs_count,
            "new_requests_count": new_requests_count,
            "rating": rating,
            "next_job": next_job_data
        }

    # Update provider services
    async def update_services(
        self, user_id: uuid.UUID, services_data: list[ServiceCategoryInput]
    ) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider profile found")

        if profile.status != ProviderStatus.APPROVED.value:
            raise ForbiddenException(
                "Only approved providers can edit their services"
            )

        # Validate categories
        category_ids = [sc.category_id for sc in services_data]
        await self._validate_categories(category_ids)

        # Sync services
        await self._sync_services(profile.id, services_data)

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    # Update provider availability
    async def update_availability(
        self, user_id: uuid.UUID, availability_data: list[AvailabilitySlotCreate]
    ) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider profile found")

        if profile.status != ProviderStatus.APPROVED.value:
            raise ForbiddenException(
                "Only approved providers can edit their availability"
            )

        # Sync availability
        await self._sync_availability(profile.id, availability_data)

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

