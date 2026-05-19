import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import PaginatedResponse, SuccessResponse, paginated_response, success_response
from app.features.auth.dependencies import get_current_user, require_admin
from app.features.providers.schemas import (
    DocumentUploadResponse,
    ProviderApplyCreate,
    ProviderDirectoryItem,
    ProviderDetailsUpdate,
    ProviderListItem,
    ProviderReapplyUpdate,
    ProviderResponse,
    ProviderReviewUpdate,
)
from app.features.providers.admin_service import ProviderAdminService
from app.features.providers.document_service import ProviderDocumentService
from app.features.providers.onboarding_service import ProviderOnboardingService
from app.features.providers.provider_profile_service import ProviderProfileService
from app.features.users.models import User
from app.utils.enums import DocumentType, ProviderStatus

router = APIRouter(prefix="/api/v1/providers", tags=["Providers"])


# Provider Onboarding Endpoints


# Submit full onboarding application
@router.post("/apply", status_code=201, response_model=SuccessResponse[ProviderResponse])
async def submit_application(
    data: ProviderApplyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderOnboardingService(db)
    profile = await service.submit_application(current_user.id, data)
    return success_response(
        data=service.map_profile_to_response(profile),
        message="Application submitted successfully",
    )


# Get current user's provider profile
@router.get("/me", response_model=SuccessResponse[ProviderResponse])
async def get_my_provider_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderOnboardingService(db)
    profile = await service.get_provider_me(current_user.id)
    return success_response(
        data=service.map_profile_to_response(profile),
    )


# Upload a verification document
@router.post(
    "/documents/upload",
    status_code=201,
    response_model=SuccessResponse[DocumentUploadResponse],
)
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    original_filename = file.filename or "unknown"

    service = ProviderDocumentService(db)
    doc = await service.upload_document(
        user_id=current_user.id,
        document_type=document_type,
        file_bytes=file_bytes,
        content_type=content_type,
        original_filename=original_filename,
    )
    return success_response(
        data=service.map_document_to_response(doc),
        message="Document uploaded successfully",
    )


# Delete an uploaded document
@router.delete("/documents/{document_id}", response_model=SuccessResponse)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderDocumentService(db)
    await service.delete_document(current_user.id, document_id)
    return success_response(message="Document deleted successfully")


# Re-apply after rejection
@router.put("/reapply", response_model=SuccessResponse[ProviderResponse])
async def reapply(
    data: ProviderReapplyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderOnboardingService(db)
    profile = await service.reapply(current_user.id, data)
    return success_response(
        data=service.map_profile_to_response(profile),
        message="Application resubmitted successfully",
    )


# --- Provider Edit Endpoints ---


# Update basic provider details
@router.patch("/me", response_model=SuccessResponse[ProviderResponse])
async def update_provider_details(
    data: ProviderDetailsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderProfileService(db)
    profile = await service.update_details(current_user.id, data)
    return success_response(
        data=service.map_profile_to_response(profile),
        message="Provider details updated",
    )


# Upload banner image
@router.post("/me/banner", response_model=SuccessResponse[ProviderResponse])
async def upload_banner_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    service = ProviderProfileService(db)
    profile = await service.upload_banner(
        current_user.id, file_bytes, content_type
    )
    return success_response(
        data=service.map_profile_to_response(profile),
        message="Banner image uploaded",
    )


# Delete banner image
@router.delete("/me/banner", response_model=SuccessResponse[ProviderResponse])
async def delete_banner_image(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderProfileService(db)
    profile = await service.delete_banner(current_user.id)
    return success_response(
        data=service.map_profile_to_response(profile),
        message="Banner image removed",
    )


# --- Admin Endpoints ---


@router.get("/directory", response_model=PaginatedResponse[ProviderDirectoryItem])
async def list_provider_directory(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderAdminService(db)
    providers, total = await service.list_providers(
        page=page,
        limit=limit,
        status_filter=ProviderStatus.APPROVED,
        search=None,
        exclude_user_id=current_user.id,
    )
    return paginated_response(
        data=[service.map_directory_item(p) for p in providers],
        page=page,
        limit=limit,
        total=total,
    )


# List all provider applications
@router.get("", response_model=PaginatedResponse[ProviderListItem])
async def list_providers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: ProviderStatus | None = Query(None),
    search: str | None = Query(None),
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderAdminService(db)
    providers, total = await service.list_providers(
        page=page, limit=limit, status_filter=status, search=search,
    )
    return paginated_response(
        data=[service.map_list_item(p) for p in providers],
        page=page,
        limit=limit,
        total=total,
    )


# Get a specific provider's full details
@router.get("/{provider_id}", response_model=SuccessResponse[ProviderResponse])
async def get_provider_detail(
    provider_id: uuid.UUID,
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderAdminService(db)
    profile = await service.get_provider_by_id(provider_id)
    return success_response(
        data=service.map_profile_to_response(profile),
    )


# Approve or reject an application (admin)
@router.patch("/{provider_id}/review", response_model=SuccessResponse[ProviderResponse])
async def review_application(
    provider_id: uuid.UUID,
    data: ProviderReviewUpdate,
    _admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderAdminService(db)
    profile = await service.review_application(
        provider_id=provider_id,
        action=data.action,
        rejection_reason=data.rejection_reason,
    )

    action_msg = "approved" if data.action.value == "approve" else f"{data.action.value}ed"

    return success_response(
        data=service.map_profile_to_response(profile),
        message=f"Provider {action_msg} successfully",
    )
