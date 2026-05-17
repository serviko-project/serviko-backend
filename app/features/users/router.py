import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import PaginatedResponse, SuccessResponse, paginated_response, success_response
from app.core.storage import StorageBucket, delete_file, upload_file
from app.features.auth.dependencies import get_current_user, get_verified_firebase_token, require_admin
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserResponse, UserUpdate
from app.features.users.service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


# UserResponse dict 
def _user_response_data(user: User) -> dict:
    response = UserResponse.model_validate(user)
    if user.provider_profile and not user.provider_profile.is_deleted:
        response.provider_status = user.provider_profile.status
    return response.model_dump(mode="json")


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
        data=_user_response_data(user),
        message="User profile created",
    )


# Get current user's profile
@router.get("/me", description="Get the profile of the currently authenticated user", response_model=SuccessResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=_user_response_data(current_user),
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
        data=_user_response_data(updated),
        message="User profile updated successfully",
    )


# Upload profile image
@router.post("/me/profile-image", response_model=SuccessResponse[UserResponse])
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Delete old image from storage if it exists
    if current_user.profile_image_url:
        delete_file(StorageBucket.PROFILE_IMAGES, current_user.profile_image_url)

    # Upload new image
    public_url = upload_file(
        bucket=StorageBucket.PROFILE_IMAGES,
        folder=str(current_user.id),
        file_bytes=file_bytes,
        content_type=content_type,
    )

    service = UserService(db)
    updated = await service.update_profile_image(current_user.id, public_url)
    return success_response(
        data=_user_response_data(updated),
        message="Profile image uploaded",
    )


# Delete profile image
@router.delete("/me/profile-image", response_model=SuccessResponse[UserResponse])
async def remove_profile_image(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.profile_image_url:
        delete_file(StorageBucket.PROFILE_IMAGES, current_user.profile_image_url)

    service = UserService(db)
    updated = await service.clear_profile_image(current_user.id)
    return success_response(
        data=_user_response_data(updated),
        message="Profile image removed",
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
        data=_user_response_data(user),
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
        data=[_user_response_data(user) for user in users],
        page=page,
        limit=limit,
        total=total,
    )
