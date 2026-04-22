import enum


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class CategoryStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
