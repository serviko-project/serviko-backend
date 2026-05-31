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
from app.features.reviews.schemas import ReviewCreate, ReviewResponse
from app.features.reviews.service import ReviewService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/reviews", tags=["Reviews"])


@router.post("", response_model=SuccessResponse[ReviewResponse], status_code=201)
async def create_review(
    body: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ReviewService(db)
    review = await svc.create_review(current_user.id, body)

    data = {
        "id": review.id,
        "booking_id": review.booking_id,
        "customer_id": review.customer_id,
        "customer_name": review.customer.full_name if review.customer else None,
        "customer_image": review.customer.profile_image_url if review.customer else None,
        "provider_id": review.provider_id,
        "provider_service_id": review.provider_service_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
    }
    return success_response(data=data, message="Review submitted successfully")


@router.get("", response_model=PaginatedResponse[ReviewResponse])
async def list_provider_reviews(
    provider_id: uuid.UUID = Query(...),
    rating: int | None = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    svc = ReviewService(db)
    reviews, total = await svc.get_provider_reviews(provider_id, rating, page, limit)

    mapped_reviews = []
    for r in reviews:
        mapped_reviews.append({
            "id": r.id,
            "booking_id": r.booking_id,
            "customer_id": r.customer_id,
            "customer_name": r.customer.full_name if r.customer else None,
            "customer_image": r.customer.profile_image_url if r.customer else None,
            "provider_id": r.provider_id,
            "provider_service_id": r.provider_service_id,
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at,
        })

    return paginated_response(data=mapped_reviews, page=page, limit=limit, total=total)


@router.get("/stats", response_model=SuccessResponse[dict])
async def get_provider_reviews_stats(
    provider_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    svc = ReviewService(db)
    stats = await svc.get_provider_reviews_stats(provider_id)
    return success_response(data=stats)
