import uuid
from datetime import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.providers.models import (
    ProviderProfile,
    ProviderService,
)


class ProviderBaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_profile_by_user_id(
        self, user_id: uuid.UUID
    ) -> ProviderProfile | None:
        result = await self.db.execute(
            select(ProviderProfile)
            .where(
                ProviderProfile.user_id == user_id,
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
        return result.scalar_one_or_none()

    def _parse_time(self, time_str: str) -> time:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))

    def map_profile_to_response(self, profile: ProviderProfile) -> dict:
        from app.core.storage import StorageBucket, create_signed_url

        # Build services list
        services = []
        for ps in (profile.services or []):
            cat = ps.category
            services.append({
                "id": ps.id,
                "category_id": ps.category_id,
                "category_title": cat.title if cat else "Unknown",
                "category_icon": cat.icon if cat else "help_outline",
                "base_price_per_hour": ps.base_price_per_hour,
            })

        # Build availability list
        availability_list = []
        for av in (profile.availability or []):
            availability_list.append({
                "id": av.id,
                "day_of_week": av.day_of_week,
                "is_enabled": av.is_enabled,
                "start_time": av.start_time.strftime("%H:%M") if av.start_time else None,
                "end_time": av.end_time.strftime("%H:%M") if av.end_time else None,
            })

        # Build documents list
        documents = []
        for doc in (profile.documents or []):
            signed_url = create_signed_url(
                StorageBucket.PROVIDER_DOCUMENTS,
                doc.file_path,
                expires_in=3600,
            )
            documents.append({
                "id": doc.id,
                "document_type": doc.document_type,
                "file_url": signed_url,
                "original_filename": doc.original_filename,
            })

        user = profile.user
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "user_name": user.full_name if user else None,
            "email": user.email if user else None,
            "phone_number": user.phone_number if user else None,
            "user_profile_image_url": user.profile_image_url if user else None,
            "professional_title": profile.professional_title,
            "years_of_experience": profile.years_of_experience,
            "about": profile.about,
            "status": profile.status,
            "rejection_reason": profile.rejection_reason,
            "submitted_at": profile.submitted_at,
            "reviewed_at": profile.reviewed_at,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "coverage_radius_km": profile.coverage_radius_km,
            "banner_image_url": profile.banner_image_url,
            "services": services,
            "availability": availability_list,
            "documents": documents,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }

    def map_document_to_response(self, doc) -> dict:
        from app.core.storage import StorageBucket, create_signed_url
        signed_url = create_signed_url(
            StorageBucket.PROVIDER_DOCUMENTS,
            doc.file_path,
            expires_in=3600,
        )
        return {
            "id": doc.id,
            "document_type": doc.document_type,
            "file_url": signed_url,
            "original_filename": doc.original_filename,
        }
