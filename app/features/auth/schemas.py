import uuid

from pydantic import BaseModel, Field, field_validator


class RecoveryOptionsRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


class RecoveryOptionsData(BaseModel):
    account_exists: bool = True
    email: str
    has_email_method: bool
    has_phone_method: bool
    masked_email: str
    masked_phone: str | None = None


class PasswordResetPhoneStartRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


class PasswordResetPhoneStartData(BaseModel):
    reset_session_id: uuid.UUID
    expires_in: int
    resend_available_in: int


class PasswordResetPhoneVerifyRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    reset_session_id: uuid.UUID
    otp: str = Field(..., min_length=4, max_length=4)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("OTP must contain only digits")
        return value


class PasswordResetPhoneVerifyData(BaseModel):
    verification_token: str
    expires_in_seconds: int


class PasswordResetPhoneCompleteRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    verification_token: str
    new_password: str = Field(..., min_length=6, max_length=128)
