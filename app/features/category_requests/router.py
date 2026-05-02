import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import (
    PaginatedResponse,
    SuccessResponse,
    paginated_response,
    success_response,
)
from app.features.auth.dependencies import get_current_user, require_admin
from app.features.category_requests.schemas import (
    CategoryRequestCounts,
    CategoryRequestCreate,
    CategoryRequestResponse,
    CategoryRequestReview,
)
from app.features.category_requests.service import CategoryRequestService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/category-requests", tags=["Category Requests"])


# Build response dict from CategoryRequest 
def _request_response(request) -> dict:
    return CategoryRequestResponse(
        id=request.id,
        user_id=request.user_id,
        provider_name=request.user.full_name if request.user else None,
        provider_avatar_url=request.user.profile_image_url if request.user else None,
        requested_category=request.title,
        description=request.description,
        status=request.status,
        admin_note=request.admin_note,
        submitted_at=request.created_at,
        reviewed_at=request.reviewed_at,
        provider_profile_id=request.user.provider_profile.id
        if request.user and request.user.provider_profile
        else None,
    ).model_dump(mode="json")


# Provider: submit a category request
@router.post(
    "",
    status_code=201,
    response_model=SuccessResponse[CategoryRequestResponse],
)
async def create_category_request(
    data: CategoryRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryRequestService(db)
    request = await service.create_request(current_user.id, data)
    return success_response(
        data=_request_response(request),
        message="Category request submitted",
    )


# Provider: get my requests
@router.get(
    "/me",
    response_model=SuccessResponse[list[CategoryRequestResponse]],
)
async def get_my_category_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryRequestService(db)
    requests = await service.get_my_requests(current_user.id)
    return success_response(
        data=[_request_response(r) for r in requests],
    )


# Admin: get counts per status
@router.get(
    "/counts",
    response_model=SuccessResponse[CategoryRequestCounts],
    dependencies=[Depends(require_admin)],
)
async def get_request_counts(
    db: AsyncSession = Depends(get_db),
):
    service = CategoryRequestService(db)
    counts = await service.get_request_counts()
    return success_response(data=counts)


# Admin: list all requests
@router.get(
    "",
    response_model=PaginatedResponse[CategoryRequestResponse],
    dependencies=[Depends(require_admin)],
)
async def list_category_requests(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryRequestService(db)
    requests, total = await service.list_requests(status, page, limit)
    return paginated_response(
        data=[_request_response(r) for r in requests],
        page=page,
        limit=limit,
        total=total,
    )


# Admin: review a request (approve or decline)
@router.patch(
    "/{request_id}/review",
    response_model=SuccessResponse[CategoryRequestResponse],
    dependencies=[Depends(require_admin)],
)
async def review_category_request(
    request_id: uuid.UUID,
    data: CategoryRequestReview,
    db: AsyncSession = Depends(get_db),
):
    service = CategoryRequestService(db)
    request = await service.review_request(request_id, data)
    return success_response(
        data=_request_response(request),
        message=f"Category request {data.action.value}d",
    )
