from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: Optional[T] = None
    message: str = "Success"


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: list[T]
    meta: PaginationMeta


def success_response(
    data: Any = None,
    message: str = "Success",
) -> dict:
    return {
        "status": "success",
        "data": data,
        "message": message,
    }


def paginated_response(
    data: list,
    page: int,
    limit: int,
    total: int,
) -> dict:
    return {
        "status": "success",
        "data": data,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
        },
    }
