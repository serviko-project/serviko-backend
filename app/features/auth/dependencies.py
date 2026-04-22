from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.firebase import verify_firebase_token
from app.features.users.models import User
from app.features.users.service import UserService


async def get_current_user(
    authorization: str = Header(..., description="Bearer <firebase_token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Invalid authorization header format")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedException("Missing authentication token")

    # Verify with Firebase
    decoded = verify_firebase_token(token)

    # Look up user in DB
    service = UserService(db)
    user = await service.get_user_by_firebase_uid(decoded["uid"])
    if user is None:
        raise UnauthorizedException(
            "User profile not found. Please complete registration.")

    return user


async def require_admin(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
) -> bool:
    settings = get_settings()
    if x_admin_key != settings.ADMIN_API_KEY:
        raise ForbiddenException("Invalid admin key")
    return True
