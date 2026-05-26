import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import PaginatedResponse, SuccessResponse, paginated_response, success_response
from app.features.auth.dependencies import get_current_user
from app.features.users.models import User
from app.features.bookmarks.schemas import BookmarkCreate, BookmarkResponse
from app.features.bookmarks.service import BookmarkService
from app.features.services.schemas import ServiceResponse

router = APIRouter(prefix="/api/v1/bookmarks", tags=["Bookmarks"])

def _map_service_detail(service) -> dict:
    provider_services = service.provider.services if service.provider else []
    total_reviews = sum(ps.reviews_count for ps in provider_services)
    aggregate_rating = 0.0
    if total_reviews > 0:
        aggregate_rating = sum(
            ps.rating * ps.reviews_count for ps in provider_services
        ) / total_reviews

    return {
        "id": service.id,
        "category_id": service.category_id,
        "category_name": service.category.title if service.category else "",
        "category_icon": service.category.icon if service.category else "",
        "provider_id": service.provider_id,
        "provider_name": service.provider.user.full_name if service.provider and service.provider.user else "Unknown",
        "provider_image": service.provider.user.profile_image_url if service.provider and service.provider.user else None,
        "provider_firebase_uid": service.provider.user.firebase_uid if service.provider and service.provider.user else None,
        "banner_image": service.provider.banner_image_url if service.provider else None,
        "professional_title": service.provider.professional_title if service.provider else None,
        "base_price_per_hour": service.base_price_per_hour or 0.0,
        "rating": round(aggregate_rating, 2),
        "reviews_count": total_reviews,
        "years_of_experience": service.provider.years_of_experience if service.provider else None,
        "latitude": service.provider.latitude if service.provider else None,
        "longitude": service.provider.longitude if service.provider else None,
        "is_bookmarked": True,
    }

@router.post("", status_code=201, response_model=SuccessResponse[BookmarkResponse])
async def add_bookmark(
    data: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BookmarkService(db)
    bookmark = await service.add_bookmark(current_user.id, data.service_id)
    return success_response(
        data=BookmarkResponse.model_validate(bookmark),
        message="Service bookmarked successfully",
    )

@router.delete("/{service_id}", response_model=SuccessResponse[None])
async def remove_bookmark(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BookmarkService(db)
    await service.remove_bookmark(current_user.id, service_id)
    return success_response(
        message="Service unbookmarked successfully"
    )

@router.get("", response_model=PaginatedResponse[ServiceResponse])
async def list_bookmarks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BookmarkService(db)
    services, total = await service.list_user_bookmarks(current_user.id, page, limit)
    return paginated_response(
        data=[_map_service_detail(s) for s in services],
        page=page,
        limit=limit,
        total=total
    )
