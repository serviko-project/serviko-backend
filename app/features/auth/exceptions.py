from app.core.exceptions import ServikoException


class EmailNotRegisteredException(ServikoException):
    def __init__(self):
        super().__init__(
            message="Email is not registered",
            status_code=404,
            error_code="EMAIL_NOT_REGISTERED",
        )


class RecoveryMethodUnavailableException(ServikoException):
    def __init__(self):
        super().__init__(
            message="Phone recovery is not available for this account",
            status_code=400,
            error_code="RECOVERY_METHOD_UNAVAILABLE",
        )


class RecoveryRateLimitException(ServikoException):
    def __init__(self, message: str = "Too many recovery requests. Try again later"):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMITED",
        )


class OtpCooldownException(ServikoException):
    def __init__(self, retry_after_seconds: int):
        super().__init__(
            message=f"OTP resend is on cooldown. Retry after {retry_after_seconds} seconds",
            status_code=429,
            error_code="OTP_COOLDOWN_ACTIVE",
        )


class InvalidResetSessionException(ServikoException):
    def __init__(self):
        super().__init__(
            message="Invalid or expired reset session",
            status_code=404,
            error_code="INVALID_RESET_SESSION",
        )


class OtpExpiredException(ServikoException):
    def __init__(self):
        super().__init__(
            message="OTP has expired",
            status_code=400,
            error_code="OTP_EXPIRED",
        )


class OtpSessionLockedException(ServikoException):
    def __init__(self):
        super().__init__(
            message="OTP verification is temporarily locked",
            status_code=423,
            error_code="OTP_SESSION_LOCKED",
        )


class InvalidOtpException(ServikoException):
    def __init__(self):
        super().__init__(
            message="Invalid OTP",
            status_code=400,
            error_code="INVALID_OTP",
        )


class WeakPasswordException(ServikoException):
    def __init__(self):
        super().__init__(
            message="Password must be at least 6 characters",
            status_code=422,
            error_code="WEAK_PASSWORD",
        )


class PasswordResetFailedException(ServikoException):
    def __init__(self):
        super().__init__(
            message="Unable to reset password at this time",
            status_code=500,
            error_code="PASSWORD_RESET_FAILED",
        )
