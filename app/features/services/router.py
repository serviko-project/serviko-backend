import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import PaginatedResponse, SuccessResponse, paginated_response, success_response
from app.features.services.schemas import ServiceResponse, ServiceDetailResponse
from app.features.services.service import SearchService
from app.features.auth.dependencies import get_current_user
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/services", tags=["Services"])


def _map_service_detail(service) -> dict:
    data = {
        "id": service.id,
        "category_id": service.category_id,
        "category_name": service.category.title if service.category else "",
        "category_icon": service.category.icon if service.category else "",
        "provider_id": service.provider_id,
        "provider_name": service.provider.user.full_name if service.provider and service.provider.user else "Unknown",
        "provider_image": service.provider.user.profile_image_url if service.provider and service.provider.user else None,
        "banner_image": service.provider.banner_image_url if service.provider else None,
        "professional_title": service.provider.professional_title if service.provider else None,
        "base_price_per_hour": service.base_price_per_hour or 0.0,
        "rating": 4.5,
        "reviews_count": 100,
        "years_of_experience": service.provider.years_of_experience if service.provider else None,
        "latitude": service.provider.latitude if service.provider else None,
        "longitude": service.provider.longitude if service.provider else None,
        "about": service.provider.about if service.provider else None,
        "gallery_images": [],
        "all_categories": [
            {
                "category_id": ps.category_id,
                "category_name": ps.category.title,
                "base_price_per_hour": ps.base_price_per_hour or 0.0
            } for ps in service.provider.services if ps.category
        ] if service.provider else []
    }
    return data


@router.get("", response_model=PaginatedResponse[ServiceResponse])
async def list_services(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search_query: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = SearchService(db)
    services, total = await service.list_services(page, limit, current_user.id, search_query, category_id)

    return paginated_response(
        data=[_map_service_detail(s) for s in services],
        page=page,
        limit=limit,
        total=total
    )


@router.get("/popular", response_model=SuccessResponse[list[ServiceResponse]])
async def list_popular_services(
    category_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = SearchService(db)
    services = await service.list_popular_services(current_user.id, category_id)

    return success_response(
        data=[_map_service_detail(s) for s in services]
    )


@router.get("/{service_id}", response_model=SuccessResponse[ServiceDetailResponse])
async def get_service_detail(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = SearchService(db)
    s = await service.get_service_detail(service_id)

    return success_response(
        data=_map_service_detail(s)
    )
