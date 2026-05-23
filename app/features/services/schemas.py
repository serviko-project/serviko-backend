import uuid
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ServiceResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_icon: str
    provider_id: uuid.UUID
    provider_name: str
    provider_image: Optional[str] = None
    provider_firebase_uid: Optional[str] = None
    banner_image: Optional[str] = None
    professional_title: Optional[str] = None
    base_price_per_hour: float
    rating: float
    reviews_count: int
    years_of_experience: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderServiceInfo(BaseModel):
    category_id: uuid.UUID
    category_name: str
    base_price_per_hour: float


class ServiceDetailResponse(ServiceResponse):
    about: Optional[str] = None
    gallery_images: List[str] = []
    all_categories: List[ProviderServiceInfo] = []
