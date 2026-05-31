import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import (
    PaginatedResponse,
    SuccessResponse,
    paginated_response,
    success_response,
)
from app.features.auth.dependencies import get_current_user, require_admin
from app.features.notifications.schemas import (
    DeviceTokenRegister,
    DeviceTokenRemove,
    NotificationResponse,
    UnreadCountResponse,
)
from app.features.notifications.service import NotificationService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1", tags=["Notifications"])


@router.post("/devices", status_code=201)
async def register_device_token(
    body: DeviceTokenRegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    await svc.register_device_token(
        user_id=current_user.id,
        fcm_token=body.fcm_token,
        device_type=body.device_type,
    )
    return success_response(message="Device token registered")


@router.delete("/devices")
async def remove_device_token(
    body: DeviceTokenRemove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    await svc.remove_device_token(
        user_id=current_user.id,
        fcm_token=body.fcm_token,
    )
    return success_response(message="Device token removed")


@router.get(
    "/notifications",
    response_model=PaginatedResponse[NotificationResponse],
)
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    notifications, total = await svc.list_notifications(
        user_id=current_user.id,
        page=page,
        limit=limit,
    )

    data = [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "data": n.data,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifications
    ]

    return paginated_response(data=data, page=page, limit=limit, total=total)


@router.get(
    "/notifications/unread-count",
    response_model=SuccessResponse[UnreadCountResponse],
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    count = await svc.get_unread_count(current_user.id)
    return success_response(data={"count": count})


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    await svc.mark_as_read(notification_id, current_user.id)
    return success_response(message="Notification marked as read")


@router.patch("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    await svc.mark_all_read(current_user.id)
    return success_response(message="All notifications marked as read")


@router.post("/notifications/cleanup")
async def cleanup_notifications(
    _: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Clean up old/expired notifications from DB
    svc = NotificationService(db)
    count = await svc.cleanup_old_notifications()
    await db.commit()
    return success_response(
        message=f"Cleaned up {count} expired notifications",
        data={"cleaned_count": count},
    )
