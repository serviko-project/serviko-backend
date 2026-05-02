import enum


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class CategoryStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProviderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class DocumentType(str, enum.Enum):
    GOVERNMENT_ID = "government_id"
    PROFESSIONAL_CERTIFICATE = "professional_certificate"


class ReviewAction(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    BLOCK = "block"


class CategoryRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class CategoryRequestAction(str, enum.Enum):
    APPROVE = "approve"
    DECLINE = "decline"
