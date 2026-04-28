import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from firebase_admin import auth
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.auth.exceptions import (
    EmailNotRegisteredException,
    InvalidOtpException,
    InvalidResetSessionException,
    OtpCooldownException,
    OtpExpiredException,
    OtpSessionLockedException,
    PasswordResetFailedException,
    RecoveryMethodUnavailableException,
)
from app.features.auth.utils import (
    hash_otp,
    mask_email,
    mask_phone,
    normalize_email,
    normalize_phone_e164,
    validate_password_policy,
    verify_otp,
)
from app.features.auth.otp_session_model import PasswordResetSession
from app.features.auth.rate_limiter import AuthRateLimiter
from app.features.auth.schemas import (
    PasswordResetPhoneCompleteRequest,
    PasswordResetPhoneStartData,
    PasswordResetPhoneStartRequest,
    PasswordResetPhoneVerifyData,
    PasswordResetPhoneVerifyRequest,
    RecoveryOptionsData,
    RecoveryOptionsRequest,
)
from app.features.auth.sms_provider import get_sms_provider
from app.features.users.models import User

logger = logging.getLogger(__name__)


class AuthRecoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.sms_provider = get_sms_provider(self.settings)
        self.rate_limiter = AuthRateLimiter(
            db=db,
            max_requests=self.settings.RECOVERY_RATE_LIMIT_MAX_REQUESTS,
            window_seconds=self.settings.RECOVERY_RATE_LIMIT_WINDOW_SECONDS,
        )

    async def get_recovery_options(self, payload: RecoveryOptionsRequest, ip_address: str) -> RecoveryOptionsData:
        email = normalize_email(payload.email)
        await self.rate_limiter.enforce(
            endpoint="recovery_options",
            email=email,
            ip_address=ip_address,
        )

        user = await self._get_user_by_email(email)
        if user is None:
            raise EmailNotRegisteredException()

        raw_phone = (user.phone_number or "").strip()
        has_phone_method = bool(raw_phone)

        return RecoveryOptionsData(
            account_exists=True,
            email=email,
            has_email_method=True,
            has_phone_method=has_phone_method,
            masked_email=mask_email(email),
            masked_phone=mask_phone(raw_phone) if has_phone_method else None,
        )

    async def start_phone_password_reset(
        self,
        payload: PasswordResetPhoneStartRequest,
        ip_address: str,
    ) -> PasswordResetPhoneStartData:
        email = normalize_email(payload.email)
        await self.rate_limiter.enforce(
            endpoint="phone_start",
            email=email,
            ip_address=ip_address,
        )

        user = await self._get_user_by_email(email)
        phone_e164 = normalize_phone_e164(
            user.phone_number) if user and user.phone_number else None
        if user is None or not phone_e164:
            raise RecoveryMethodUnavailableException()

        now = datetime.now(UTC)
        latest_session = await self._get_latest_active_session(email)
        if latest_session:
            cooldown_ends_at = latest_session.created_at + timedelta(
                seconds=self.settings.OTP_RESEND_COOLDOWN_SECONDS
            )
            if cooldown_ends_at > now:
                retry_after = int((cooldown_ends_at - now).total_seconds())
                raise OtpCooldownException(
                    retry_after_seconds=max(retry_after, 1))

        otp_code = f"{secrets.randbelow(9000) + 1000:04d}"
        otp_hash = hash_otp(otp_code)
        expires_at = now + timedelta(seconds=self.settings.OTP_EXPIRY_SECONDS)

        session = PasswordResetSession(
            email=email,
            phone_e164=phone_e164,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        await self.sms_provider.send_otp(phone_e164, otp_code)

        return PasswordResetPhoneStartData(
            reset_session_id=session.id,
            expires_in=self.settings.OTP_EXPIRY_SECONDS,
            resend_available_in=self.settings.OTP_RESEND_COOLDOWN_SECONDS,
        )

    async def verify_phone_password_reset(
        self,
        payload: PasswordResetPhoneVerifyRequest,
        ip_address: str,
    ) -> PasswordResetPhoneVerifyData:
        session = await self._get_session_for_verification(payload.reset_session_id)
        if session is None or session.email != normalize_email(payload.email):
            raise InvalidResetSessionException()

        await self.rate_limiter.enforce(
            endpoint="phone_verify",
            email=session.email,
            ip_address=ip_address,
        )

        now = datetime.now(UTC)
        if session.locked_until and session.locked_until > now:
            raise OtpSessionLockedException()

        if session.expires_at <= now:
            raise OtpExpiredException()

        if not verify_otp(payload.otp, session.otp_hash):
            session.attempts += 1
            if session.attempts >= self.settings.OTP_MAX_VERIFY_ATTEMPTS:
                session.locked_until = now + \
                    timedelta(minutes=self.settings.OTP_LOCK_MINUTES)

            await self.db.flush()

            raise InvalidOtpException()

        session.verification_token = secrets.token_urlsafe(32)
        await self.db.flush()

        return PasswordResetPhoneVerifyData(
            verification_token=session.verification_token,
            expires_in_seconds=int((session.expires_at - now).total_seconds()),
        )

    async def complete_phone_password_reset(
        self,
        payload: PasswordResetPhoneCompleteRequest,
        ip_address: str,
    ) -> None:
        validate_password_policy(payload.new_password)

        session = await self._get_session_by_token(payload.verification_token)
        if session is None or session.email != normalize_email(payload.email):
            raise InvalidResetSessionException()

        await self.rate_limiter.enforce(
            endpoint="phone_complete",
            email=session.email,
            ip_address=ip_address,
        )

        now = datetime.now(UTC)
        if session.expires_at <= now:
            raise OtpExpiredException()

        user = await self._get_user_by_email(session.email)
        if user is None:
            raise InvalidResetSessionException()

        try:
            auth.update_user(user.firebase_uid, password=payload.new_password)
        except Exception as exc:
            logger.error(
                "firebase_password_reset_failed uid=%s reason=%s", user.firebase_uid, str(exc))
            raise PasswordResetFailedException() from exc

        session.consumed_at = now
        session.otp_hash = ""
        session.verification_token = None
        session.locked_until = None
        await self.db.flush()

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email)
        )
        return result.scalar_one_or_none()

    async def _get_latest_active_session(self, email: str) -> PasswordResetSession | None:
        stmt: Select[tuple[PasswordResetSession]] = (
            select(PasswordResetSession)
            .where(
                PasswordResetSession.email == email,
                PasswordResetSession.consumed_at.is_(None),
                PasswordResetSession.expires_at > datetime.now(UTC),
            )
            .order_by(PasswordResetSession.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_session_for_verification(self, session_id: Any) -> PasswordResetSession | None:
        stmt: Select[tuple[PasswordResetSession]] = select(PasswordResetSession).where(
            PasswordResetSession.id == session_id,
            PasswordResetSession.consumed_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_session_by_token(self, verification_token: str) -> PasswordResetSession | None:
        stmt: Select[tuple[PasswordResetSession]] = select(PasswordResetSession).where(
            PasswordResetSession.verification_token == verification_token,
            PasswordResetSession.consumed_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
