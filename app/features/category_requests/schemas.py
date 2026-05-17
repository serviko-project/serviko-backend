import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.utils.enums import CategoryRequestAction


# Provider submits a category request
class CategoryRequestCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    proposed_base_price: float = Field(..., gt=0, le=10000)


class CategoryRequestReview(BaseModel):
    action: CategoryRequestAction
    icon: str | None = Field(None, min_length=1, max_length=50)
    admin_note: str | None = Field(None, max_length=500)
    title: str | None = Field(None, min_length=1, max_length=100)
    category_status: str | None = Field(None, max_length=20)


# API response
class CategoryRequestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider_name: str | None = None
    provider_avatar_url: str | None = None
    requested_category: str
    description: str | None = None
    proposed_base_price: float
    status: str
    admin_note: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None
    provider_profile_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


# Status counts for admin tabs
class CategoryRequestCounts(BaseModel):
    pending: int = 0
    approved: int = 0
    declined: int = 0
