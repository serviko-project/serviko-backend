class ServikoException(Exception):
    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class NotFoundException(ServikoException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
        )


class UnauthorizedException(ServikoException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(ServikoException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class ConflictException(ServikoException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
        )


class ValidationException(ServikoException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
        )
