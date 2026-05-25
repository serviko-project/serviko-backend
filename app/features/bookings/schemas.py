import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    service_id: uuid.UUID
    scheduled_date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    duration_hours: int = Field(..., ge=1, le=8)
    customer_latitude: float | None = None
    customer_longitude: float | None = None
    customer_address: str | None = Field(None, max_length=500)
    promo_code: str | None = Field(None, max_length=30)


class BookingReviewUpdate(BaseModel):
    action: str = Field(..., pattern=r"^(confirm|reject)$")
    rejection_reason: str | None = Field(None, max_length=1000)


class BookingCompleteUpdate(BaseModel):
    completion_note: str | None = Field(None, max_length=1000)


# Lightweight list item
class BookingListItem(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    service_id: uuid.UUID
    status: str
    scheduled_date: date
    start_time: str
    end_time: str
    duration_hours: int
    base_price_per_hour: float
    total_price: float
    original_price: float | None = None
    discount_amount: float = 0.0
    promo_code_text: str | None = None
    customer_latitude: float | None = None
    customer_longitude: float | None = None
    customer_address: str | None = None
    customer_name: str | None = None
    customer_image: str | None = None
    customer_firebase_uid: str | None = None
    provider_name: str | None = None
    provider_image: str | None = None
    provider_firebase_uid: str | None = None
    category_name: str | None = None
    rejection_reason: str | None = None
    completion_note: str | None = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    payment_status: str = "unpaid"
    payment_id: uuid.UUID | None = None
    payment_reference: str | None = None
    paid_at: datetime | None = None
    refunded_at: datetime | None = None
    has_review: bool = False
    created_at: datetime
    updated_at: datetime


# Full detail response
class BookingResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    service_id: uuid.UUID
    status: str
    scheduled_date: date
    start_time: str
    end_time: str
    duration_hours: int
    base_price_per_hour: float
    total_price: float
    original_price: float | None = None
    discount_amount: float = 0.0
    promo_code_text: str | None = None
    customer_latitude: float | None = None
    customer_longitude: float | None = None
    customer_address: str | None = None
    rejection_reason: str | None = None
    customer_name: str | None = None
    customer_image: str | None = None
    customer_firebase_uid: str | None = None
    provider_name: str | None = None
    provider_image: str | None = None
    provider_firebase_uid: str | None = None
    category_name: str | None = None
    rejection_reason: str | None = None
    completion_note: str | None = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    payment_status: str = "unpaid"
    payment_id: uuid.UUID | None = None
    payment_reference: str | None = None
    paid_at: datetime | None = None
    refunded_at: datetime | None = None
    has_review: bool = False
    created_at: datetime
    updated_at: datetime


# Available slots response
class AvailableSlotsResponse(BaseModel):
    date: date
    provider_id: uuid.UUID
    slots: list[str]
    max_duration_from_slot: dict[str, int] = {}
