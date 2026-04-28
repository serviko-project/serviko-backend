import uuid
from datetime import time, datetime, timezone

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.core.storage import StorageBucket, create_signed_url, delete_file, upload_file
from app.features.categories.models import Category
from app.features.providers.models import (
    ProviderAvailability,
    ProviderDocument,
    ProviderProfile,
    ProviderService,
)
from app.features.providers.schemas import ProviderApplyCreate, ProviderReapplyUpdate
from app.utils.enums import DocumentType, ProviderStatus, ReviewAction


class ProviderApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create_draft(self, user_id: uuid.UUID) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if profile:
            return profile

        profile = ProviderProfile(
            user_id=user_id, status=ProviderStatus.DRAFT.value)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

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

    # Parse Time
    def _parse_time(self, time_str: str) -> time:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))

    # --- Submit application ---
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

        # Validate that all category IDs exist
        cat_result = await self.db.execute(
            select(func.count(Category.id)).where(
                Category.id.in_(data.service_category_ids),
                Category.is_deleted == False,
            )
        )
        valid_count = cat_result.scalar_one()
        if valid_count != len(data.service_category_ids):
            raise ValidationException(
                "One or more selected categories are invalid")

        # Update profile fields
        profile.professional_title = data.professional_title
        profile.years_of_experience = data.years_of_experience
        profile.about = data.about
        profile.latitude = data.latitude
        profile.longitude = data.longitude
        profile.coverage_radius_km = data.coverage_radius_km
        profile.status = ProviderStatus.PENDING.value
        profile.submitted_at = datetime.now(timezone.utc)

        # Clear old services and availability
        await self.db.execute(
            delete(ProviderService).where(
                ProviderService.provider_id == profile.id
            )
        )
        await self.db.execute(
            delete(ProviderAvailability).where(
                ProviderAvailability.provider_id == profile.id
            )
        )

        # Add services
        for cat_id in data.service_category_ids:
            self.db.add(
                ProviderService(provider_id=profile.id, category_id=cat_id)
            )

        # Add availability slots
        for slot in data.availability:
            self.db.add(
                ProviderAvailability(
                    provider_id=profile.id,
                    day_of_week=slot.day_of_week,
                    is_enabled=slot.is_enabled,
                    start_time=self._parse_time(slot.start_time),
                    end_time=self._parse_time(slot.end_time),
                )
            )

        await self.db.flush()

        # Re-fetch with relationships
        return await self._get_profile_by_user_id(user_id)

    # --- Get provider profile for /me ---
    async def get_provider_me(self, user_id: uuid.UUID) -> ProviderProfile:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider application found")
        return profile

    # --- Get provider by ID (admin) ---
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

    # --- List providers ---
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

    # --- Admin review (approve/reject) ---
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

    # --- Re-apply after rejection ---
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
        cat_result = await self.db.execute(
            select(func.count(Category.id)).where(
                Category.id.in_(data.service_category_ids),
                Category.is_deleted == False,
            )
        )
        valid_count = cat_result.scalar_one()
        if valid_count != len(data.service_category_ids):
            raise ValidationException(
                "One or more selected categories are invalid")

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

        # Replace services
        await self.db.execute(
            delete(ProviderService).where(
                ProviderService.provider_id == profile.id
            )
        )
        for cat_id in data.service_category_ids:
            self.db.add(
                ProviderService(provider_id=profile.id, category_id=cat_id)
            )

        # Replace availability
        await self.db.execute(
            delete(ProviderAvailability).where(
                ProviderAvailability.provider_id == profile.id
            )
        )
        for slot in data.availability:
            self.db.add(
                ProviderAvailability(
                    provider_id=profile.id,
                    day_of_week=slot.day_of_week,
                    is_enabled=slot.is_enabled,
                    start_time=self._parse_time(slot.start_time),
                    end_time=self._parse_time(slot.end_time),
                )
            )

        await self.db.flush()
        return await self._get_profile_by_user_id(user_id)

    # --- Upload document ---
    async def upload_document(
        self,
        user_id: uuid.UUID,
        document_type: DocumentType,
        file_bytes: bytes,
        content_type: str,
        original_filename: str,
    ) -> ProviderDocument:
        # Get or create draft profile
        profile = await self._get_or_create_draft(user_id)

        # Cannot upload docs for an already approved profile
        if profile.status == ProviderStatus.APPROVED.value:
            raise ValidationException(
                "Cannot upload documents for an approved application"
            )

        # Upload to Supabase
        folder = f"providers/{user_id}/{document_type.value}"
        file_path = upload_file(
            bucket=StorageBucket.PROVIDER_DOCUMENTS,
            folder=folder,
            file_bytes=file_bytes,
            content_type=content_type,
        )

        # Check if a document of this type already exists
        existing = None
        if profile.documents:
            for doc in profile.documents:
                if doc.document_type == document_type.value:
                    existing = doc
                    break

        if existing:
            # Delete old file from storage
            delete_file(StorageBucket.PROVIDER_DOCUMENTS, existing.file_path)

            # Update existing record
            existing.file_path = file_path
            existing.original_filename = original_filename
            existing.file_size_bytes = len(file_bytes)
            existing.mime_type = content_type
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            # Create new document record
            doc = ProviderDocument(
                provider_id=profile.id,
                document_type=document_type.value,
                file_path=file_path,
                original_filename=original_filename,
                file_size_bytes=len(file_bytes),
                mime_type=content_type,
            )
            self.db.add(doc)
            await self.db.flush()
            await self.db.refresh(doc)
            return doc

    # --- Delete document ---
    async def delete_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider application found")

        # Cannot delete docs for an approved profile
        if profile.status == ProviderStatus.APPROVED.value:
            raise ValidationException(
                "Cannot delete documents for an approved application"
            )

        # Find the document
        target_doc = None
        if profile.documents:
            for doc in profile.documents:
                if doc.id == document_id:
                    target_doc = doc
                    break

        if not target_doc:
            raise NotFoundException("Document not found")

        # Delete from Supabase
        delete_file(StorageBucket.PROVIDER_DOCUMENTS, target_doc.file_path)

        # Delete from DB
        await self.db.execute(
            delete(ProviderDocument).where(ProviderDocument.id == document_id)
        )
        await self.db.flush()

    # Helper Functions to build response dicts from models
    def build_provider_response(self, profile: ProviderProfile) -> dict:
        # Build services list with category info
        services = []
        for ps in (profile.services or []):
            cat = ps.category
            services.append({
                "id": ps.id,
                "category_id": ps.category_id,
                "category_title": cat.title if cat else "Unknown",
                "category_icon": cat.icon if cat else "help_outline",
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

        # Build documents list with signed URLs
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
            "services": services,
            "availability": availability_list,
            "documents": documents,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }

    # Build summary dict for admin listing
    def build_list_item(self, profile: ProviderProfile) -> dict:
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

    # Build document upload response with signed URL
    def build_document_response(self, doc: ProviderDocument) -> dict:
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
