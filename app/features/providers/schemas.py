import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.utils.enums import DocumentType, ProviderStatus, ReviewAction


# Availability slot for a specific day of the week
class AvailabilitySlotCreate(BaseModel):
    day_of_week: int = Field(..., ge=1, le=7)
    is_enabled: bool
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")


# Full provider application payload
class ProviderApplyCreate(BaseModel):
    professional_title: str = Field(..., min_length=1, max_length=150)
    years_of_experience: int = Field(..., ge=0, le=50)
    about: str | None = Field(None, max_length=2000)
    service_category_ids: list[uuid.UUID] = Field(..., min_length=1)
    availability: list[AvailabilitySlotCreate] = Field(..., min_length=7, max_length=7)
    latitude: float | None = None
    longitude: float | None = None
    coverage_radius_km: float = Field(15.0, ge=1.0, le=50.0)


# Re-application payload 
class ProviderReapplyUpdate(BaseModel):
    professional_title: str = Field(..., min_length=1, max_length=150)
    years_of_experience: int = Field(..., ge=0, le=50)
    about: str | None = Field(None, max_length=2000)
    service_category_ids: list[uuid.UUID] = Field(..., min_length=1)
    availability: list[AvailabilitySlotCreate] = Field(..., min_length=7, max_length=7)
    latitude: float | None = None
    longitude: float | None = None
    coverage_radius_km: float = Field(15.0, ge=1.0, le=50.0)


# Admin review action
class ProviderReviewUpdate(BaseModel):
    action: ReviewAction
    rejection_reason: str | None = Field(None, max_length=1000)


# --- Response Schemas ---

class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    document_type: DocumentType
    file_url: str
    original_filename: str

    model_config = {"from_attributes": True}


class ProviderDocumentResponse(BaseModel):
    id: uuid.UUID
    document_type: DocumentType
    file_url: str
    original_filename: str

    model_config = {"from_attributes": True}


class ProviderServiceResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_title: str
    category_icon: str

    model_config = {"from_attributes": True}


class ProviderAvailabilityResponse(BaseModel):
    id: uuid.UUID
    day_of_week: int
    is_enabled: bool
    start_time: str
    end_time: str

    model_config = {"from_attributes": True}


# Full provider profile response 
class ProviderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str | None = None
    user_profile_image_url: str | None = None
    professional_title: str | None = None
    years_of_experience: int | None = None
    about: str | None = None
    status: ProviderStatus
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    coverage_radius_km: float | None = None
    services: list[ProviderServiceResponse] = []
    availability: list[ProviderAvailabilityResponse] = []
    documents: list[ProviderDocumentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Summary for admin listing
class ProviderListItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str | None = None
    professional_title: str | None = None
    status: ProviderStatus
    submitted_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
