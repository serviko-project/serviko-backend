import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, distinct
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.features.providers.base_service import ProviderBaseService
from app.features.providers.models import (
    ProviderProfile,
    ProviderService,
)
from app.features.categories.models import Category
from app.features.users.models import User
from app.utils.enums import ProviderStatus, ReviewAction


class ProviderAdminService(ProviderBaseService):
    async def list_providers(
        self,
        page: int = 1,
        limit: int = 20,
        status_filter: ProviderStatus | None = None,
        search: str | None = None,
        exclude_user_id: uuid.UUID | None = None,
    ) -> tuple[list[ProviderProfile], int]:
        limit = min(limit, 100)
        offset = (page - 1) * limit

        base_filter = [
            ProviderProfile.is_deleted == False,
            ProviderProfile.status != ProviderStatus.DRAFT.value,
        ]
        if status_filter:
            base_filter.append(ProviderProfile.status == status_filter.value)
        if exclude_user_id:
            base_filter.append(ProviderProfile.user_id != exclude_user_id)

        # Search by name, email, title or category
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            base_filter.append(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    ProviderProfile.professional_title.ilike(pattern),
                    Category.title.ilike(pattern),
                )
            )

        # Count (join User and Category for search)
        count_query = (
            select(func.count(distinct(ProviderProfile.id)))
            .join(User, ProviderProfile.user_id == User.id)
            .outerjoin(ProviderService, ProviderProfile.id == ProviderService.provider_id)
            .outerjoin(Category, ProviderService.category_id == Category.id)
            .where(*base_filter)
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Paginated results with user + services loaded
        result = await self.db.execute(
            select(ProviderProfile)
            .join(User, ProviderProfile.user_id == User.id)
            .outerjoin(ProviderService, ProviderProfile.id == ProviderService.provider_id)
            .outerjoin(Category, ProviderService.category_id == Category.id)
            .where(*base_filter)
            .options(
                selectinload(ProviderProfile.user),
                selectinload(ProviderProfile.services).selectinload(
                    ProviderService.category
                ),
            )
            .group_by(ProviderProfile.id, User.id)
            .order_by(ProviderProfile.submitted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        providers = list(result.scalars().unique().all())

        return providers, total

    async def get_provider_by_id(
        self, provider_id: uuid.UUID
    ) -> ProviderProfile:
        result = await self.db.execute(
            select(ProviderProfile)
            .where(
                ProviderProfile.id == provider_id,
                ProviderProfile.is_deleted == False,
            )
            .options(
                selectinload(ProviderProfile.services).selectinload(
                    ProviderService.category
                ),
                selectinload(ProviderProfile.availability),
                selectinload(ProviderProfile.documents),
                selectinload(ProviderProfile.user),
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundException("Provider application not found")
        return profile

    async def review_application(
        self,
        provider_id: uuid.UUID,
        action: ReviewAction,
        rejection_reason: str | None = None,
    ) -> ProviderProfile:
        profile = await self.get_provider_by_id(provider_id)

        if action == ReviewAction.APPROVE:
            if profile.status not in [ProviderStatus.PENDING.value, ProviderStatus.REJECTED.value, ProviderStatus.BLOCKED.value]:
                raise ValidationException(
                    f"Cannot approve an application with status '{profile.status}'."
                )
            profile.status = ProviderStatus.APPROVED.value
        elif action == ReviewAction.REJECT:
            if profile.status != ProviderStatus.PENDING.value:
                raise ValidationException(
                    f"Cannot reject an application with status '{profile.status}'."
                )
            if not rejection_reason:
                raise ValidationException(
                    "Rejection reason is required when rejecting an application"
                )
            profile.status = ProviderStatus.REJECTED.value
            profile.rejection_reason = rejection_reason
        elif action == ReviewAction.BLOCK:
            if profile.status != ProviderStatus.APPROVED.value:
                raise ValidationException(
                    f"Cannot block an application with status '{profile.status}'."
                )
            profile.status = ProviderStatus.BLOCKED.value

        profile.reviewed_at = datetime.now(timezone.utc)

        await self.db.flush()
        return await self.get_provider_by_id(provider_id)

    def map_list_item(self, profile: ProviderProfile) -> dict:
        user = profile.user
        categories = []
        for ps in (profile.services or []):
            cat = ps.category
            if cat:
                categories.append(cat.title)

        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "user_name": user.full_name if user else None,
            "email": user.email if user else None,
            "phone_number": user.phone_number if user else None,
            "user_profile_image_url": user.profile_image_url if user else None,
            "professional_title": profile.professional_title,
            "status": profile.status,
            "categories": categories,
            "submitted_at": profile.submitted_at,
            "created_at": profile.created_at,
        }

    def map_directory_item(self, profile: ProviderProfile) -> dict:
        user = profile.user
        categories = []
        for ps in (profile.services or []):
            cat = ps.category
            if cat:
                categories.append(cat.title)

        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "firebase_uid": user.firebase_uid if user else "",
            "user_name": user.full_name if user else None,
            "user_profile_image_url": user.profile_image_url if user else None,
            "professional_title": profile.professional_title,
            "about": profile.about,
            "banner_image_url": profile.banner_image_url,
            "categories": categories,
            "created_at": profile.created_at,
        }
