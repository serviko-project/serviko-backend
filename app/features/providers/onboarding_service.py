import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.features.categories.models import Category
from app.features.providers.base_service import ProviderBaseService
from app.features.providers.models import (
    ProviderAvailability,
    ProviderProfile,
    ProviderService,
)
from app.features.providers.schemas import ProviderApplyCreate, ProviderReapplyUpdate
from app.utils.enums import ProviderStatus


class ProviderOnboardingService(ProviderBaseService):
    async def submit_application(
        self, user_id: uuid.UUID, data: ProviderApplyCreate
    ) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)

        # Check for existing non-draft profile
        if profile and profile.status != ProviderStatus.DRAFT.value:
            raise ConflictException(
                "You already have an active provider application")

        # Create draft if none exists
        if not profile:
            profile = ProviderProfile(
                user_id=user_id, status=ProviderStatus.DRAFT.value
            )
            self.db.add(profile)
            await self.db.flush()
            await self.db.refresh(profile)

        # Validate that both documents are uploaded
        doc_count = len(profile.documents) if profile.documents else 0
        if doc_count < 2:
            raise ValidationException(
                "Both Government ID and Professional Certificate must be uploaded before submitting"
            )

        # Validate categories
        await self._validate_categories(data.service_category_ids)

        # Update profile fields
        profile.professional_title = data.professional_title
        profile.years_of_experience = data.years_of_experience
        profile.about = data.about
        profile.latitude = data.latitude
        profile.longitude = data.longitude
        profile.coverage_radius_km = data.coverage_radius_km
        profile.status = ProviderStatus.PENDING.value
        profile.submitted_at = datetime.now(timezone.utc)

        # Sync services and availability
        await self._sync_services(profile.id, data.service_category_ids)
        await self._sync_availability(profile.id, data.availability)

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    async def reapply(
        self, user_id: uuid.UUID, data: ProviderReapplyUpdate
    ) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider application found to reapply")

        if profile.status != ProviderStatus.REJECTED.value:
            raise ValidationException(
                "Only rejected applications can be resubmitted"
            )

        # Validate documents still exist
        doc_count = len(profile.documents) if profile.documents else 0
        if doc_count < 2:
            raise ValidationException(
                "Both documents must be uploaded before resubmitting"
            )

        # Validate categories
        await self._validate_categories(data.service_category_ids)

        # Update profile
        profile.professional_title = data.professional_title
        profile.years_of_experience = data.years_of_experience
        profile.about = data.about
        profile.latitude = data.latitude
        profile.longitude = data.longitude
        profile.coverage_radius_km = data.coverage_radius_km
        profile.status = ProviderStatus.PENDING.value
        profile.rejection_reason = None
        profile.reviewed_at = None
        profile.submitted_at = datetime.now(timezone.utc)

        # Sync services and availability
        await self._sync_services(profile.id, data.service_category_ids)
        await self._sync_availability(profile.id, data.availability)

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    async def get_provider_me(self, user_id: uuid.UUID) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider application found")
        return profile

    # --- Helpers ---

    async def _validate_categories(self, category_ids: list[uuid.UUID]):
        cat_result = await self.db.execute(
            select(func.count(Category.id)).where(
                Category.id.in_(category_ids),
                Category.is_deleted == False,
            )
        )
        valid_count = cat_result.scalar_one()
        if valid_count != len(category_ids):
            raise ValidationException(
                "One or more selected categories are invalid")

    async def _sync_services(self, provider_id: uuid.UUID, category_ids: list[uuid.UUID]):
        await self.db.execute(
            delete(ProviderService).where(
                ProviderService.provider_id == provider_id
            )
        )
        for cat_id in category_ids:
            self.db.add(
                ProviderService(provider_id=provider_id, category_id=cat_id)
            )

    async def _sync_availability(self, provider_id: uuid.UUID, availability_data: list):
        await self.db.execute(
            delete(ProviderAvailability).where(
                ProviderAvailability.provider_id == provider_id
            )
        )
        for slot in availability_data:
            self.db.add(
                ProviderAvailability(
                    provider_id=provider_id,
                    day_of_week=slot.day_of_week,
                    is_enabled=slot.is_enabled,
                    start_time=self._parse_time(slot.start_time),
                    end_time=self._parse_time(slot.end_time),
                )
            )
