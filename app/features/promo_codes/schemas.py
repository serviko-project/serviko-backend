import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PromoCodeCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=30)
    description: str | None = Field(None, max_length=200)
    discount_type: str = Field(..., pattern=r"^(percentage|flat)$")
    discount_value: float = Field(..., gt=0)
    min_booking_amount: float | None = Field(None, ge=0)
    max_uses: int | None = Field(None, ge=1)
    max_discount_amount: float | None = Field(None, ge=0)
    expires_at: datetime | None = None


class PromoCodeUpdate(BaseModel):
    description: str | None = Field(None, max_length=200)
    is_active: bool | None = None
    min_booking_amount: float | None = None
    max_uses: int | None = Field(None, ge=1)
    max_discount_amount: float | None = None
    expires_at: datetime | None = None


class PromoCodeResponse(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    code: str
    description: str | None = None
    discount_type: str
    discount_value: float
    min_booking_amount: float | None = None
    max_uses: int | None = None
    max_uses_per_customer: int
    is_active: bool
    usage_count: int = 0
    max_discount_amount: float | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PromoCodeValidateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    service_id: uuid.UUID


class PromoCodeValidateResponse(BaseModel):
    valid: bool
    promo_code_id: uuid.UUID | None = None
    code: str
    discount_type: str | None = None
    discount_value: float | None = None
    estimated_discount: float | None = None
    message: str
