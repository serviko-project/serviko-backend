import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BookmarkCreate(BaseModel):
    service_id: uuid.UUID

class BookmarkResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    service_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
