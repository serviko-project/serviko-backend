import logging
import uuid
from datetime import datetime, timedelta, timezone

from firebase_admin import messaging
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import DeviceToken, Notification

logger = logging.getLogger(__name__)

# Retention period for old notifications
NOTIFICATION_RETENTION_DAYS = 90


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Device Token Management --
    async def register_device_token(
        self,
        user_id: uuid.UUID,
        fcm_token: str,
        device_type: str = "android",
    ) -> DeviceToken:
        # Check if token already exists
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.fcm_token == fcm_token)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Reassign token to current user if different
            existing.user_id = user_id
            existing.device_type = device_type
            existing.is_active = True
            await self.db.flush()
            return existing

        token = DeviceToken(
            user_id=user_id,
            fcm_token=fcm_token,
            device_type=device_type,
            is_active=True,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def remove_device_token(
        self,
        user_id: uuid.UUID,
        fcm_token: str,
    ) -> None:
        await self.db.execute(
            delete(DeviceToken).where(
                DeviceToken.user_id == user_id,
                DeviceToken.fcm_token == fcm_token,
            )
        )
        await self.db.flush()

    async def _get_user_fcm_tokens(self, user_id: uuid.UUID) -> list[str]:
        result = await self.db.execute(
            select(DeviceToken.fcm_token).where(
                DeviceToken.user_id == user_id,
                DeviceToken.is_active == True,
            )
        )
        return list(result.scalars().all())

    # -- Send Notifications --

    async def send_to_user(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        notification_type: str,
        data: dict | None = None,
    ) -> Notification | None:
        # Save to DB
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            data=data,
            is_read=False,
        )
        self.db.add(notification)
        await self.db.flush()

        # Send FCM push
        tokens = await self._get_user_fcm_tokens(user_id)
        if tokens:
            await self._send_fcm_multicast(
                tokens=tokens,
                title=title,
                body=body,
                data=self._prepare_fcm_data(notification, data),
            )

        return notification

    async def _send_fcm_multicast(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> None:
        if not tokens:
            return

        message = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="serviko_channel",
                    priority="high",
                    default_sound=True,
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound="default",
                        badge=1,
                    ),
                ),
            ),
        )

        try:
            response = messaging.send_each_for_multicast(message)
            logger.info(
                "FCM multicast: %d success, %d failure",
                response.success_count,
                response.failure_count,
            )

            # Deactivate invalid tokens
            if response.failure_count > 0:
                await self._handle_failed_tokens(tokens, response.responses)
        except Exception as e:
            logger.error("FCM send error: %s", str(e))

    async def _handle_failed_tokens(
        self,
        tokens: list[str],
        responses: list,
    ) -> None:
        invalid_tokens = []
        for i, resp in enumerate(responses):
            if resp.exception and isinstance(
                resp.exception,
                (
                    messaging.UnregisteredError,
                    messaging.SenderIdMismatchError,
                ),
            ):
                invalid_tokens.append(tokens[i])

        if invalid_tokens:
            await self.db.execute(
                update(DeviceToken)
                .where(DeviceToken.fcm_token.in_(invalid_tokens))
                .values(is_active=False)
            )
            logger.info("Deactivated %d invalid FCM tokens",
                        len(invalid_tokens))

    def _prepare_fcm_data(
        self,
        notification: Notification,
        data: dict | None,
    ) -> dict[str, str]:
        fcm_data = {
            "notification_id": str(notification.id),
            "type": notification.type,
        }
        if data:
            for key, value in data.items():
                fcm_data[key] = str(value)
        return fcm_data

    # -- Notification Feed --

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Notification], int]:
        limit = min(limit, 50)

        count_result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
            )
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        notifications = list(result.scalars().all())

        return notifications, total

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar_one()

    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.flush()

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        await self.db.flush()

    async def cleanup_old_notifications(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=NOTIFICATION_RETENTION_DAYS,
        )
        result = await self.db.execute(
            delete(Notification).where(Notification.created_at < cutoff)
        )
        await self.db.flush()
        return result.rowcount or 0
