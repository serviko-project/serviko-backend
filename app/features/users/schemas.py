import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.utils.enums import Gender


# Create User profile after Firebase signup
class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str | None = Field(None, max_length=20)
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image_url: str | None = Field(None, max_length=2048)
    latitude: float | None = None
    longitude: float | None = None


# Partial update of User profile
class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=100)
    phone_number: str | None = Field(None, max_length=20)
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image_url: str | None = Field(None, max_length=2048)
    latitude: float | None = None
    longitude: float | None = None


# API response
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image_url: str | None = None
    is_active: bool
    latitude: float | None = None
    longitude: float | None = None
    provider_status: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
