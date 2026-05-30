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
from app.features.providers.schemas import ProviderApplyCreate, ProviderReapplyUpdate, ServiceCategoryInput
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
        category_ids = [sc.category_id for sc in data.service_categories]
        await self._validate_categories(category_ids)

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
        await self._sync_services(profile.id, data.service_categories)
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
        category_ids = [sc.category_id for sc in data.service_categories]
        await self._validate_categories(category_ids)

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
        await self._sync_services(profile.id, data.service_categories)
        await self._sync_availability(profile.id, data.availability)

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    async def get_provider_me(self, user_id: uuid.UUID) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider application found")
        return profile
