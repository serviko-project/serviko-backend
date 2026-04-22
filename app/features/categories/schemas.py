import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.utils.enums import CategoryStatus


# Create a new category 
class CategoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)
    status: CategoryStatus = CategoryStatus.ACTIVE


# Partial update 
class CategoryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    icon: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)
    status: CategoryStatus | None = None


# API response
class CategoryResponse(BaseModel):
    id: uuid.UUID
    title: str
    icon: str
    description: str | None = None
    status: CategoryStatus
    provider_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
