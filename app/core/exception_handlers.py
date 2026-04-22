import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import ServikoException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    # Handle custom ServikoException hierarchy
    @app.exception_handler(ServikoException)
    async def serviko_exception_handler(
        request: Request, exc: ServikoException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "detail": exc.message,
                "code": exc.error_code,
            },
        )

    # Handle Pydantic validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append(f"{field}: {error['msg']}")

        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "detail": "; ".join(errors),
                "code": "VALIDATION_ERROR",
            },
        )

    # Catch-all for unhandled exceptions
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception: %s\n%s",
            str(exc),
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": "An internal server error occurred",
                "code": "INTERNAL_ERROR",
            },
        )
