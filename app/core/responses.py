from typing import Any


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
