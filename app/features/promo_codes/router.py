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
from app.features.auth.dependencies import get_current_user
from app.features.promo_codes.schemas import (
    PromoCodeCreate,
    PromoCodeResponse,
    PromoCodeUpdate,
    PromoCodeValidateRequest,
    PromoCodeValidateResponse,
    ActivePromoCodeResponse,
)
from app.features.promo_codes.services import ProviderPromoService, ValidationPromoService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/promo-codes", tags=["Promo Codes"])


@router.post("", response_model=SuccessResponse[PromoCodeResponse], status_code=201)
async def create_promo_code(
    body: PromoCodeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProviderPromoService(db)
    result = await svc.create_promo_code(current_user.id, body.model_dump())
    return success_response(data=result, message="Promo code created")


@router.get("", response_model=PaginatedResponse[PromoCodeResponse])
async def list_promo_codes(
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProviderPromoService(db)
    if provider_id:
        items, total = await svc.list_promos_by_provider_id(provider_id, page, limit)
    else:
        items, total = await svc.list_provider_promos(current_user.id, page, limit)
    return paginated_response(data=items, page=page, limit=limit, total=total)


@router.get("/active", response_model=PaginatedResponse[ActivePromoCodeResponse])
async def list_active_promo_codes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProviderPromoService(db)
    items, total = await svc.list_all_active_promos(current_user.id, page, limit)
    return paginated_response(data=items, page=page, limit=limit, total=total)


@router.patch("/{promo_id}", response_model=SuccessResponse[PromoCodeResponse])
async def update_promo_code(
    promo_id: uuid.UUID,
    body: PromoCodeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProviderPromoService(db)
    result = await svc.update_promo_code(
        promo_id, current_user.id, body.model_dump(exclude_unset=True),
    )
    return success_response(data=result, message="Promo code updated")


@router.delete("/{promo_id}", response_model=SuccessResponse[PromoCodeResponse])
async def deactivate_promo_code(
    promo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProviderPromoService(db)
    result = await svc.deactivate_promo_code(promo_id, current_user.id)
    return success_response(data=result, message="Promo code deactivated")


@router.post(
    "/validate",
    response_model=SuccessResponse[PromoCodeValidateResponse],
)
async def validate_promo_code(
    body: PromoCodeValidateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Look up the provider from the service_id
    from app.features.bookings.base_service import BookingBaseService
    base_svc = BookingBaseService(db)
    provider_service = await base_svc._get_provider_service(body.service_id)

    svc = ValidationPromoService(db)
    base_price = provider_service.base_price_per_hour or 0.0
    result = await svc.validate_and_calculate(
        code=body.code,
        provider_id=provider_service.provider_id,
        customer_id=current_user.id,
        subtotal=base_price,
    )
    return success_response(data=result, message=result["message"])
