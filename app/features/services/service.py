import uuid
from typing import List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.features.providers.models import ProviderService, ProviderProfile
from app.features.categories.models import Category
from app.features.users.models import User
from app.core.exceptions import NotFoundException


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_services(
        self,
        page: int,
        limit: int,
        current_user_id: uuid.UUID,
        search_query: str | None = None,
        category_id: uuid.UUID | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_rating: float | None = None,
        min_experience: int | None = None,
        max_experience: int | None = None
    ) -> Tuple[List[ProviderService], int]:
        query = (
            select(ProviderService)
            .join(ProviderService.provider)
            .join(ProviderService.category)
            .join(ProviderProfile.user)
            .where(ProviderProfile.status == "approved")
            .where(ProviderProfile.is_deleted == False)
            .where(Category.status == "active")
            .where(ProviderProfile.user_id != current_user_id)
        )

        if category_id:
            query = query.where(ProviderService.category_id == category_id)

        if min_price is not None:
            query = query.where(
                ProviderService.base_price_per_hour >= min_price)

        if max_price is not None:
            query = query.where(
                ProviderService.base_price_per_hour <= max_price)

        if min_experience is not None:
            query = query.where(
                ProviderProfile.years_of_experience >= min_experience)

        if max_experience is not None:
            query = query.where(
                ProviderProfile.years_of_experience <= max_experience)

        if min_rating is not None:
            query = query.where(ProviderService.rating >= min_rating)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                (Category.title.ilike(search_pattern)) |
                (User.full_name.ilike(search_pattern)) |
                (ProviderProfile.professional_title.ilike(search_pattern))
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginate
        query = query.offset((page - 1) * limit).limit(limit)

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

    async def list_popular_services(self, current_user_id: uuid.UUID, category_id: uuid.UUID | None = None) -> List[ProviderService]:
        query = (
            select(ProviderService)
            .join(ProviderService.provider)
            .join(ProviderService.category)
            .join(ProviderProfile.user)
            .where(ProviderProfile.status == "approved")
            .where(ProviderProfile.is_deleted == False)
            .where(Category.status == "active")
            .where(ProviderProfile.user_id != current_user_id)
        )

        if category_id:
            query = query.where(ProviderService.category_id == category_id)

        query = query.limit(5)

        query = query.options(
            joinedload(ProviderService.category),
            joinedload(ProviderService.provider).options(
                joinedload(ProviderProfile.user),
                selectinload(ProviderProfile.services).joinedload(
                    ProviderService.category)
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_service_detail(self, service_id: uuid.UUID) -> ProviderService:
        query = (
            select(ProviderService)
            .where(ProviderService.id == service_id)
            .options(
                joinedload(ProviderService.category),
                joinedload(ProviderService.provider).options(
                    joinedload(ProviderProfile.user),
                    selectinload(ProviderProfile.services).joinedload(
                        ProviderService.category)
                )
            )
        )

        result = await self.db.execute(query)
        service = result.scalar_one_or_none()

        if not service:
            raise NotFoundException("Service not found")

        if service.provider.status != "approved" or service.provider.is_deleted or service.category.status != "active":
            raise NotFoundException("Service not found")

        return service

    async def get_price_range(self, category_id: uuid.UUID | None = None) -> dict:
        query = (
            select(
                func.min(ProviderService.base_price_per_hour).label("min_price"),
                func.max(ProviderService.base_price_per_hour).label("max_price")
            )
            .join(ProviderService.provider)
            .join(ProviderService.category)
            .where(ProviderProfile.status == "approved")
            .where(ProviderProfile.is_deleted == False)
            .where(Category.status == "active")
        )
        if category_id:
            query = query.where(ProviderService.category_id == category_id)

        result = await self.db.execute(query)
        row = result.fetchone()

        min_price = row.min_price if row and row.min_price is not None else 0.0
        max_price = row.max_price if row and row.max_price is not None else 500.0

        if min_price == max_price:
            if min_price == 0:
                max_price = 500.0
            else:
                max_price = min_price + 100.0

        return {"min_price": float(min_price), "max_price": float(max_price)}
