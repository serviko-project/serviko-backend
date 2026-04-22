import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import paginated_response, success_response
from app.features.auth.dependencies import require_admin
from app.features.categories.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.features.categories.service import CategoryService

router = APIRouter(prefix="/api/v1/categories", tags=["Categories"])


# Admin: create a new category
@router.post("", status_code=201)
async def create_category(
    data: CategoryCreate,
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    category = await service.create_category(data)
    return success_response(
        data=CategoryResponse.model_validate(category).model_dump(mode="json"),
        message="Category created successfully",
    )


# List categories with optional filters
@router.get("", description="List categories with optional status filter and search")
async def list_categories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status (active/inactive)"),
    search: str | None = Query(None, description="Search by category title"),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    categories, total = await service.list_categories(
        page=page, limit=limit, status=status, search=search,
    )
    return paginated_response(
        data=[
            CategoryResponse.model_validate(cat).model_dump(mode="json")
            for cat in categories
        ],
        page=page,
        limit=limit,
        total=total,
    )


# Get a single category by ID
@router.get("/{category_id}", description="Get a category by ID")
async def get_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    category = await service.get_category_by_id(category_id)
    return success_response(
        data=CategoryResponse.model_validate(category).model_dump(mode="json"),
    )


# Admin: update a category
@router.patch("/{category_id}", description="Update a category")
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    updated = await service.update_category(category_id, data)
    return success_response(
        data=CategoryResponse.model_validate(updated).model_dump(mode="json"),
        message="Category updated successfully",
    )


# Admin: soft delete a category
@router.delete("/{category_id}", status_code=204, description="Delete a category")
async def delete_category(
    category_id: uuid.UUID,
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    await service.delete_category(category_id)
