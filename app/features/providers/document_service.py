import uuid
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.core.storage import StorageBucket, delete_file, upload_file
from app.features.providers.base_service import ProviderBaseService
from app.features.providers.models import (
    ProviderDocument,
    ProviderProfile,
)
from app.utils.enums import DocumentType, ProviderStatus


class ProviderDocumentService(ProviderBaseService):
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
        existing = next(
            (doc for doc in (profile.documents or [])
             if doc.document_type == document_type.value),
            None
        )

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

    async def delete_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        from sqlalchemy import delete

        profile = await self._get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("No provider application found")

        # Cannot delete docs for an approved profile
        if profile.status == ProviderStatus.APPROVED.value:
            raise ValidationException(
                "Cannot delete documents for an approved application"
            )

        # Find the document
        target_doc = next(
            (doc for doc in (profile.documents or []) if doc.id == document_id),
            None
        )

        if not target_doc:
            raise NotFoundException("Document not found")

        # Delete from Supabase
        delete_file(StorageBucket.PROVIDER_DOCUMENTS, target_doc.file_path)

        # Delete from DB
        await self.db.execute(
            delete(ProviderDocument).where(ProviderDocument.id == document_id)
        )
        await self.db.flush()

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
