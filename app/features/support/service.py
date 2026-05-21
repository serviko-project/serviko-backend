import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.features.support.models import FAQ, PrivacyPolicy


class SupportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Get active FAQs with optional search and category filters
    async def list_faqs(
        self,
        category: str | None = None,
        search: str | None = None,
        is_active: bool = True
    ) -> list[FAQ]:
        query = select(FAQ).where(FAQ.is_deleted == False)

        if is_active is not None:
            query = query.where(FAQ.is_active == is_active)

        if category:
            query = query.where(FAQ.category == category.lower())

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    FAQ.question.ilike(search_filter),
                    FAQ.answer.ilike(search_filter)
                )
            )

        result = await self.db.execute(query.order_by(FAQ.category, FAQ.created_at.asc()))
        return list(result.scalars().all())

    # Get the latest active privacy policy
    async def get_latest_privacy_policy(self) -> PrivacyPolicy:
        query = select(PrivacyPolicy).where(
            PrivacyPolicy.is_active == True).order_by(PrivacyPolicy.created_at.desc())
        result = await self.db.execute(query)
        policy = result.scalars().first()
        if not policy:
            raise NotFoundException("Active privacy policy not found")
        return policy
