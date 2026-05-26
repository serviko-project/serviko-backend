import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.features.bookmarks.models import Bookmark
from app.features.providers.models import ProviderService, ProviderProfile
from app.features.categories.models import Category


class BookmarkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_bookmark(self, user_id: uuid.UUID, service_id: uuid.UUID) -> Bookmark:
        # Check if service exists and is active/approved
        service_query = (
            select(ProviderService)
            .join(ProviderService.provider)
            .join(ProviderService.category)
            .where(ProviderService.id == service_id)
            .where(ProviderProfile.status == "approved")
            .where(ProviderProfile.is_deleted == False)
            .where(Category.status == "active")
        )
        service_res = await self.db.execute(service_query)
        service = service_res.scalar_one_or_none()
        if not service:
            raise NotFoundException("Service not found")

        # Check if already bookmarked
        existing_query = select(Bookmark).where(
            Bookmark.user_id == user_id,
            Bookmark.service_id == service_id
        )
        existing_res = await self.db.execute(existing_query)
        existing = existing_res.scalar_one_or_none()
        if existing:
            raise ConflictException("Service is already bookmarked")

        bookmark = Bookmark(user_id=user_id, service_id=service_id)
        self.db.add(bookmark)
        await self.db.flush()
        await self.db.refresh(bookmark)
        return bookmark

    async def remove_bookmark(self, user_id: uuid.UUID, service_id: uuid.UUID) -> None:
        query = select(Bookmark).where(
            Bookmark.user_id == user_id,
            Bookmark.service_id == service_id
        )
        res = await self.db.execute(query)
        bookmark = res.scalar_one_or_none()
        if not bookmark:
            raise NotFoundException("Bookmark not found")

        await self.db.delete(bookmark)
        await self.db.flush()

    async def list_user_bookmarks(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20
    ) -> tuple[list[ProviderService], int]:
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Base query to fetch provider services bookmarked by the user
        query = (
            select(ProviderService)
            .join(Bookmark, Bookmark.service_id == ProviderService.id)
            .join(ProviderService.provider)
            .join(ProviderService.category)
            .where(Bookmark.user_id == user_id)
            .where(ProviderProfile.status == "approved")
            .where(ProviderProfile.is_deleted == False)
            .where(Category.status == "active")
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginated results
        query = query.offset(offset).limit(limit)

        query = query.options(
            joinedload(ProviderService.category),
            joinedload(ProviderService.provider).options(
                joinedload(ProviderProfile.user),
                selectinload(ProviderProfile.services).joinedload(
                    ProviderService.category)
            )
        )

        result = await self.db.execute(query)
        services = result.scalars().all()

        return list(services), total

    async def get_user_bookmarked_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        query = select(Bookmark.service_id).where(Bookmark.user_id == user_id)
        result = await self.db.execute(query)
        return set(result.scalars().all())
