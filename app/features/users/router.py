import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import PaginatedResponse, SuccessResponse, paginated_response, success_response
from app.features.auth.dependencies import get_current_user, get_verified_firebase_token, require_admin
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserResponse, UserUpdate
from app.features.users.service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


# Create user profile after Firebase signup
@router.post("", status_code=201, response_model=SuccessResponse[UserResponse])
async def create_user(
    data: UserCreate,
    token_data: dict = Depends(get_verified_firebase_token),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.create_user(
        firebase_uid=token_data["uid"],
        email=token_data["email"],
        data=data,
    )
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="User profile created",
    )


# Get current user's profile
@router.get("/me", description="Get the profile of the currently authenticated user", response_model=SuccessResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json"),
    )


# Update current user's profile
@router.patch("/me", description="Update the profile of the currently authenticated user", response_model=SuccessResponse[UserResponse])
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
@router.get("/{user_id}", description="Get a user's profile by ID", response_model=SuccessResponse[UserResponse])
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
@router.get("", description="List all users with pagination (admin only)", response_model=PaginatedResponse[UserResponse])
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
