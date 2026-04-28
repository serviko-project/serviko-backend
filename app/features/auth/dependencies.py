from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.firebase import verify_firebase_token
from app.features.users.models import User
from app.features.users.service import UserService

security = HTTPBearer()


async def get_verified_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    if not token:
        raise UnauthorizedException("Missing authentication token")

    # Verify with Firebase
    return verify_firebase_token(token)


async def get_current_user(
    token_data: dict = Depends(get_verified_firebase_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Look up user in DB
    service = UserService(db)
    user = await service.get_user_by_firebase_uid(token_data["uid"])
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
