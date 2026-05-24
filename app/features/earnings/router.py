from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import SuccessResponse, success_response, PaginatedResponse, paginated_response
from app.features.auth.dependencies import get_current_user
from app.features.earnings.schemas import EarningsSummaryResponse, CashOutRequest, CashOutResponse, TransactionResponse
from app.features.earnings.service import EarningsService

router = APIRouter(prefix="/api/v1/earnings", tags=["Earnings"])


@router.get("/me", response_model=SuccessResponse[EarningsSummaryResponse])
async def get_my_earnings(
    filter_type: str = Query("Weekly", alias="filter"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user.provider_profile:
        raise HTTPException(status_code=403, detail="User is not a provider")

    provider_profile_id = current_user.provider_profile.id

    result = await EarningsService.get_provider_earnings_summary(
        db=db,
        provider_id=provider_profile_id,
        filter_type=filter_type,
        start_date_str=start_date,
        end_date_str=end_date
    )
    return success_response(data=result)


@router.post("/cashout", response_model=SuccessResponse[CashOutResponse])
async def cash_out(
    request: CashOutRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user.provider_profile:
        raise HTTPException(status_code=403, detail="User is not a provider")

    provider_profile_id = current_user.provider_profile.id

    result = await EarningsService.create_cash_out(
        db=db,
        provider_id=provider_profile_id,
        request=request
    )
    return success_response(data=result)


@router.get("/transactions", response_model=PaginatedResponse[TransactionResponse])
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user.provider_profile:
        raise HTTPException(status_code=403, detail="User is not a provider")

    provider_profile_id = current_user.provider_profile.id

    transactions, total = await EarningsService.get_provider_transactions(
        db=db,
        provider_id=provider_profile_id,
        page=page,
        limit=limit
    )
    return paginated_response(
        data=transactions,
        page=page,
        limit=limit,
        total=total
    )
