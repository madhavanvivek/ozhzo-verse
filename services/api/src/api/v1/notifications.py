import math
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    NotificationModel,
    UserModel,
    UserNotificationPreferencesModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.services.notification_service import notification_service
from src.schemas.common import ApiSuccessResponse
from src.schemas.notification import (
    MessageResponse,
    NotificationDTO,
    NotificationPreferencesDTO,
    PaginatedNotificationsResponse,
    UpdateNotificationPreferencesRequest
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=ApiSuccessResponse[PaginatedNotificationsResponse])
async def list_user_notifications(
    is_read: Optional[bool] = Query(None),
    notification_type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [NotificationModel.user_id == current_user.id]

    if is_read is not None:
        filters.append(NotificationModel.is_read == is_read)
    if notification_type:
        filters.append(NotificationModel.type == notification_type)

    # Total matching count
    count_query = select(func.count()).select_from(NotificationModel).where(*filters)
    total = (await db.execute(count_query)).scalar() or 0

    # Total unread count
    unread_query = select(func.count()).select_from(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_read == False
    )
    unread_count = (await db.execute(unread_query)).scalar() or 0

    # Paginated results
    query = (
        select(NotificationModel)
        .where(*filters)
        .order_by(NotificationModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    dtos = [
        NotificationDTO(
            id=n.id,
            home_id=n.home_id,
            user_id=n.user_id,
            title=n.title,
            body=n.body,
            type=n.type,
            is_read=n.is_read,
            read_at=n.read_at,
            created_at=n.created_at
        )
        for n in notifications
    ]

    return ApiSuccessResponse(
        data=PaginatedNotificationsResponse(
            items=dtos,
            unread_count=unread_count,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.patch("/{notification_id}/read", response_model=ApiSuccessResponse[MessageResponse])
async def mark_notification_read(
    notification_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await notification_service.mark_as_read(notification_id, current_user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")

    return ApiSuccessResponse(data=MessageResponse(message="Notification marked as read."))


@router.post("/mark-all-read", response_model=ApiSuccessResponse[MessageResponse])
async def mark_all_notifications_read(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.mark_all_as_read(current_user.id, db)
    return ApiSuccessResponse(data=MessageResponse(message=f"Marked {count} notifications as read."))


@router.get("/preferences", response_model=ApiSuccessResponse[NotificationPreferencesDTO])
async def get_preferences(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = await notification_service.get_user_preferences(current_user.id, db)
    await db.commit()

    return ApiSuccessResponse(
        data=NotificationPreferencesDTO(
            in_app_enabled=pref.in_app_enabled,
            push_enabled=pref.push_enabled,
            email_enabled=pref.email_enabled,
            sms_enabled=pref.sms_enabled,
            whatsapp_enabled=pref.whatsapp_enabled,
            task_assigned_enabled=pref.task_assigned_enabled,
            bill_reminder_enabled=pref.bill_reminder_enabled,
            low_stock_enabled=pref.low_stock_enabled,
            event_reminder_enabled=pref.event_reminder_enabled,
            home_invitation_enabled=pref.home_invitation_enabled,
            system_enabled=pref.system_enabled
        )
    )


@router.patch("/preferences", response_model=ApiSuccessResponse[NotificationPreferencesDTO])
async def update_preferences(
    payload: UpdateNotificationPreferencesRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = await notification_service.get_user_preferences(current_user.id, db)

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(pref, field, val)

    pref.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=NotificationPreferencesDTO(
            in_app_enabled=pref.in_app_enabled,
            push_enabled=pref.push_enabled,
            email_enabled=pref.email_enabled,
            sms_enabled=pref.sms_enabled,
            whatsapp_enabled=pref.whatsapp_enabled,
            task_assigned_enabled=pref.task_assigned_enabled,
            bill_reminder_enabled=pref.bill_reminder_enabled,
            low_stock_enabled=pref.low_stock_enabled,
            event_reminder_enabled=pref.event_reminder_enabled,
            home_invitation_enabled=pref.home_invitation_enabled,
            system_enabled=pref.system_enabled
        )
    )
