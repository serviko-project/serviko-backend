import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DeviceTokenRegister(BaseModel):
    fcm_token: str = Field(..., min_length=1, max_length=512)
    device_type: str = Field(default="android", max_length=20)


class DeviceTokenRemove(BaseModel):
    fcm_token: str = Field(..., min_length=1, max_length=512)


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    data: dict | None = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    count: int
