import uuid
from datetime import date

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
from app.features.bookings.schemas import (
    AvailableSlotsResponse,
    BookingCreate,
    BookingListItem,
    BookingResponse,
    BookingReviewUpdate,
)
from app.features.bookings.service import BookingService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/bookings", tags=["Bookings"])


@router.get("/availability", response_model=SuccessResponse[AvailableSlotsResponse])
async def get_available_slots(
    provider_id: uuid.UUID = Query(...),
    date: date = Query(...),
    duration_hours: int = Query(1, ge=1, le=8),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    result = await svc.get_available_slots(provider_id, date, duration_hours)
    return success_response(data=result)


@router.post("", response_model=SuccessResponse[BookingResponse], status_code=201)
async def create_booking(
    body: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    booking = await svc.create_booking(current_user.id, body.model_dump())
    detail = await svc.get_booking_detail(booking.id, current_user.id)
    return success_response(data=detail, message="Booking request sent")


@router.get("", response_model=PaginatedResponse[BookingListItem])
async def list_my_bookings(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    bookings, total = await svc.list_customer_bookings(
        current_user.id, status, page, limit,
    )
    return paginated_response(data=bookings, page=page, limit=limit, total=total)


@router.get("/provider", response_model=PaginatedResponse[BookingListItem])
async def list_provider_bookings(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    bookings, total = await svc.list_provider_bookings(
        current_user.id, status, page, limit,
    )
    return paginated_response(data=bookings, page=page, limit=limit, total=total)


@router.get("/{booking_id}", response_model=SuccessResponse[BookingResponse])
async def get_booking_detail(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    detail = await svc.get_booking_detail(booking_id, current_user.id)
    return success_response(data=detail)


@router.patch(
    "/{booking_id}/review",
    response_model=SuccessResponse[BookingResponse],
)
async def review_booking(
    booking_id: uuid.UUID,
    body: BookingReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    detail = await svc.review_booking(
        booking_id, current_user.id, body.action, body.rejection_reason,
    )
    return success_response(data=detail)


@router.patch(
    "/{booking_id}/cancel",
    response_model=SuccessResponse[BookingResponse],
)
async def cancel_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = BookingService(db)
    detail = await svc.cancel_booking(booking_id, current_user.id)
    return success_response(data=detail)
