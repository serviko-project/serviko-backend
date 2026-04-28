from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.features.auth.schemas import (
    PasswordResetPhoneCompleteRequest,
    PasswordResetPhoneStartRequest,
    PasswordResetPhoneVerifyRequest,
    RecoveryOptionsRequest,
)
from app.features.auth.service import AuthRecoveryService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _resolve_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


@router.post("/recovery-options")
async def recovery_options(
    payload: RecoveryOptionsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthRecoveryService(db)
    data = await service.get_recovery_options(payload, _resolve_client_ip(request))
    return success_response(
        data=data.model_dump(mode="json"),
        message="Recovery options fetched successfully",
    )


@router.post("/password-reset/phone/start")
async def password_reset_phone_start(
    payload: PasswordResetPhoneStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthRecoveryService(db)
    data = await service.start_phone_password_reset(payload, _resolve_client_ip(request))
    return success_response(
        data=data.model_dump(mode="json"),
        message="OTP sent successfully",
    )


@router.post("/password-reset/phone/verify")
async def password_reset_phone_verify(
    payload: PasswordResetPhoneVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthRecoveryService(db)
    data = await service.verify_phone_password_reset(payload, _resolve_client_ip(request))
    return success_response(
        data=data.model_dump(mode="json"),
        message="OTP verified successfully",
    )


@router.post("/password-reset/phone/complete")
async def password_reset_phone_complete(
    payload: PasswordResetPhoneCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthRecoveryService(db)
    await service.complete_phone_password_reset(payload, _resolve_client_ip(request))
    return success_response(
        data=None,
        message="Password reset successful",
    )
