import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.features.categories.models import Category
from app.features.category_requests.models import CategoryRequest
from app.features.category_requests.schemas import (
    CategoryRequestCreate,
    CategoryRequestReview,
)
from app.features.providers.models import ProviderProfile, ProviderService
from app.utils.enums import CategoryRequestAction, CategoryRequestStatus


class CategoryRequestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Provider: submit a category request
    async def create_request(
        self, user_id: uuid.UUID, data: CategoryRequestCreate
    ) -> CategoryRequest:
        # Check for existing pending request by this user
        existing = await self.db.execute(
            select(CategoryRequest).where(
                CategoryRequest.user_id == user_id,
                CategoryRequest.status == CategoryRequestStatus.PENDING.value,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                "You already have a pending category request"
            )

        request = CategoryRequest(
            user_id=user_id,
            title=data.title,
            description=data.description,
            proposed_base_price=data.proposed_base_price,
            status=CategoryRequestStatus.PENDING.value,
        )
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    # Provider: get my requests
    async def get_my_requests(
        self, user_id: uuid.UUID
    ) -> list[CategoryRequest]:
        result = await self.db.execute(
            select(CategoryRequest)
            .where(CategoryRequest.user_id == user_id)
            .order_by(CategoryRequest.created_at.desc())
        )
        return list(result.scalars().all())

    # Admin: list requests with optional status filter
    async def list_requests(
        self,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[CategoryRequest], int]:
        limit = min(limit, 100)
        offset = (page - 1) * limit

        base_query = select(CategoryRequest)
        count_query = select(func.count(CategoryRequest.id))

        if status:
            base_query = base_query.where(CategoryRequest.status == status)
            count_query = count_query.where(CategoryRequest.status == status)

        # Total count
        total = (await self.db.execute(count_query)).scalar_one()

        # Paginated results
        result = await self.db.execute(
            base_query
            .order_by(CategoryRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        requests = list(result.scalars().all())
        return requests, total

    # Admin: get counts per status
    async def get_request_counts(self) -> dict[str, int]:
        result = await self.db.execute(
            select(
                CategoryRequest.status,
                func.count(CategoryRequest.id),
            ).group_by(CategoryRequest.status)
        )
        counts = {"pending": 0, "approved": 0, "declined": 0}
        for status, count in result.all():
            if status in counts:
                counts[status] = count
        return counts

    # Admin: review a category request (approve or decline)
    async def review_request(
        self, request_id: uuid.UUID, data: CategoryRequestReview
    ) -> CategoryRequest:
        result = await self.db.execute(
            select(CategoryRequest).where(CategoryRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        if not request:
            raise NotFoundException("Category request not found")

        if request.status != CategoryRequestStatus.PENDING.value:
            raise ValidationException("Only pending requests can be reviewed")

        if data.action == CategoryRequestAction.APPROVE:
            if not data.icon:
                raise ValidationException(
                    "Icon is required when approving a category request"
                )
            request.status = CategoryRequestStatus.APPROVED.value
            request.reviewed_at = datetime.now(timezone.utc)

            # Create the category
            category = Category(
                title=data.title or request.title,
                icon=data.icon,
                description=request.description,
                status=data.category_status or "active",
            )
            self.db.add(category)
            await self.db.flush()

            # Auto-link to provider's services if they have a profile
            provider_result = await self.db.execute(
                select(ProviderProfile).where(
                    ProviderProfile.user_id == request.user_id,
                    ProviderProfile.is_deleted == False,
                )
            )
            provider = provider_result.scalar_one_or_none()
            if provider:
                self.db.add(
                    ProviderService(
                        provider_id=provider.id,
                        category_id=category.id,
                        base_price_per_hour=request.proposed_base_price,
                    )
                )

        elif data.action == CategoryRequestAction.DECLINE:
            if not data.admin_note:
                raise ValidationException(
                    "Reason is required when declining a category request"
                )
            request.status = CategoryRequestStatus.DECLINED.value
            request.admin_note = data.admin_note
            request.reviewed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(request)
        return request
