import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    booking_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=1000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None = None
    customer_image: str | None = None
    provider_id: uuid.UUID
    provider_service_id: uuid.UUID
    rating: int
    comment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
