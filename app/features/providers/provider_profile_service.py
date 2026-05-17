import uuid

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.storage import StorageBucket, delete_file, upload_file
from app.features.providers.base_service import ProviderBaseService
from app.features.providers.models import ProviderProfile
from app.features.providers.schemas import ProviderDetailsUpdate
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
