import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
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
from app.utils.enums import ProviderStatus, ReviewAction


class ProviderAdminService(ProviderBaseService):
    async def list_providers(
        self,
        page: int = 1,
        limit: int = 20,
        status_filter: ProviderStatus | None = None,
    ) -> tuple[list[ProviderProfile], int]:
        limit = min(limit, 100)
        offset = (page - 1) * limit

        base_filter = [
            ProviderProfile.is_deleted == False,
            ProviderProfile.status != ProviderStatus.DRAFT.value,
        ]
        if status_filter:
            base_filter.append(ProviderProfile.status == status_filter.value)

        # Count
        count_result = await self.db.execute(
            select(func.count(ProviderProfile.id)).where(*base_filter)
        )
        total = count_result.scalar_one()

        # Paginated results
        result = await self.db.execute(
            select(ProviderProfile)
            .where(*base_filter)
            .options(selectinload(ProviderProfile.user))
            .order_by(ProviderProfile.submitted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        providers = list(result.scalars().all())

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

        if profile.status != ProviderStatus.PENDING.value:
            raise ValidationException(
                f"Cannot review an application with status '{profile.status}'. Only 'pending' applications can be reviewed."
            )

        if action == ReviewAction.APPROVE:
            profile.status = ProviderStatus.APPROVED.value
        elif action == ReviewAction.REJECT:
            if not rejection_reason:
                raise ValidationException(
                    "Rejection reason is required when rejecting an application"
                )
            profile.status = ProviderStatus.REJECTED.value
            profile.rejection_reason = rejection_reason

        profile.reviewed_at = datetime.now(timezone.utc)

        await self.db.flush()
        return await self.get_provider_by_id(provider_id)

    def map_list_item(self, profile: ProviderProfile) -> dict:
        user = profile.user
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "user_name": user.full_name if user else None,
            "professional_title": profile.professional_title,
            "status": profile.status,
            "submitted_at": profile.submitted_at,
            "created_at": profile.created_at,
        }
