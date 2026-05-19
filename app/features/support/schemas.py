import uuid
from datetime import datetime
from pydantic import BaseModel, Field

# Schema for FAQ response
class FAQResponse(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    category: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

# Schema for Privacy Policy response
class PrivacyPolicyResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
