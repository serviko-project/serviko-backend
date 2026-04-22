import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.features.categories.models import Category
from app.features.categories.schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Base query for active categories
    def _active_query(self):
        return select(Category).where(Category.is_deleted == False)

    # Create a new category
    async def create_category(self, data: CategoryCreate) -> Category:
        # Check for duplicate title
        result = await self.db.execute(
            self._active_query().where(Category.title == data.title)
        )
        if result.scalar_one_or_none():
            raise ConflictException(f"Category '{data.title}' already exists")

        category = Category(
            title=data.title,
            icon=data.icon,
            description=data.description,
            status=data.status.value,
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    # Get a single category by ID
    async def get_category_by_id(self, category_id: uuid.UUID) -> Category:
        result = await self.db.execute(
            self._active_query().where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFoundException("Category not found")
        return category

    # List categories with optional filters
    async def list_categories(
        self,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Category], int]:
        limit = min(limit, 100)
        offset = (page - 1) * limit

        query = self._active_query()

        # Filter by status
        if status:
            query = query.where(Category.status == status)

        # Search by title
        if search:
            query = query.where(Category.title.ilike(f"%{search}%"))

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Paginated results
        result = await self.db.execute(
            query.order_by(Category.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        categories = list(result.scalars().all())

        return categories, total

    # Update a category
    async def update_category(
        self, category_id: uuid.UUID, data: CategoryUpdate
    ) -> Category:
        category = await self.get_category_by_id(category_id)

        update_data = data.model_dump(exclude_unset=True)

        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value

        if "title" in update_data and update_data["title"] != category.title:
            result = await self.db.execute(
                self._active_query().where(
                    Category.title == update_data["title"],
                    Category.id != category_id,
                )
            )
            if result.scalar_one_or_none():
                raise ConflictException(
                    f"Category '{update_data['title']}' already exists"
                )

        for field, value in update_data.items():
            setattr(category, field, value)

        await self.db.flush()
        await self.db.refresh(category)
        return category

    # Soft delete a category
    async def delete_category(self, category_id: uuid.UUID) -> None:
        category = await self.get_category_by_id(category_id)
        category.is_deleted = True
        await self.db.flush()
