import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.firebase import verify_firebase_token
from app.core.responses import paginated_response, success_response
from app.features.auth.dependencies import get_current_user, require_admin
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserResponse, UserUpdate
from app.features.users.service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

# Create user profile after Firebase signup
@router.post("", status_code=201)
async def create_user(
    data: UserCreate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    # Verify Firebase token
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Invalid authorization header format")

    token = authorization.removeprefix("Bearer ").strip()
    decoded = verify_firebase_token(token)

    service = UserService(db)
    user = await service.create_user(
        firebase_uid=decoded["uid"],
        email=decoded["email"],
        data=data,
    )
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="User profile created",
    )


# Get current user's profile
@router.get("/me",description="Get the profile of the currently authenticated user")
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json"),
    )


# Update current user's profile
@router.patch("/me",description="Update the profile of the currently authenticated user")
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    updated = await service.update_user(current_user.id, data)
    return success_response(
        data=UserResponse.model_validate(updated).model_dump(mode="json"),
        message="User profile updated successfully",
    )


# Admin: get any user by ID
@router.get("/{user_id}", description="Get a user's profile by ID")
async def get_user(
    user_id: uuid.UUID,
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
    )


# Admin: list all users
@router.get("", description="List all users with pagination (admin only)")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    users, total = await service.list_users(page=page, limit=limit)
    return paginated_response(
        data=[
            UserResponse.model_validate(user).model_dump(mode="json")
            for user in users
        ],
        page=page,
        limit=limit,
        total=total,
    )
