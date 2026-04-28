from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.exceptions import RecoveryRateLimitException
from app.features.auth.otp_session_model import RecoveryRateLimit


class AuthRateLimiter:
    def __init__(
        self,
        db: AsyncSession,
        max_requests: int,
        window_seconds: int,
    ):
        self.db = db
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def enforce(self, endpoint: str, email: str, ip_address: str) -> None:
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=self.window_seconds)

        stmt: Select[tuple[RecoveryRateLimit]] = select(RecoveryRateLimit).where(
            RecoveryRateLimit.endpoint == endpoint,
            RecoveryRateLimit.email == email,
            RecoveryRateLimit.ip_address == ip_address,
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            record = RecoveryRateLimit(
                endpoint=endpoint,
                email=email,
                ip_address=ip_address,
                window_start=now,
                request_count=1,
                last_request_at=now,
            )
            self.db.add(record)
            await self.db.flush()
            return

        if record.window_start < window_start:
            record.window_start = now
            record.request_count = 1
            record.last_request_at = now
            await self.db.flush()
            return

        if record.request_count >= self.max_requests:
            raise RecoveryRateLimitException()

        record.request_count += 1
        record.last_request_at = now
        await self.db.flush()
