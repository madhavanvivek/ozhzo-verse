import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    HomeModel,
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
    PriorityAlertSummaryDTO,
    UpdateNotificationPreferencesRequest
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _to_dto(n: NotificationModel, home_name: Optional[str] = None) -> NotificationDTO:
    meta_dict = None
    if n.extra_metadata:
        try:
            meta_dict = json.loads(n.extra_metadata) if isinstance(n.extra_metadata, str) else n.extra_metadata
        except Exception:
            meta_dict = None

    return NotificationDTO(
        id=n.id,
        home_id=n.home_id,
        home_name=home_name or (n.home.name if hasattr(n, "home") and n.home else None),
        user_id=n.user_id,
        title=n.title,
        body=n.body,
        type=n.type,
        priority=getattr(n, "priority", "NORMAL") or "NORMAL",
        requires_action=bool(getattr(n, "requires_action", False)),
        action_status=getattr(n, "action_status", "OPEN") or "OPEN",
        action_type=getattr(n, "action_type", None),
        action_url=getattr(n, "action_url", None),
        action_label=getattr(n, "action_label", None),
        extra_metadata=meta_dict,
        is_read=bool(n.is_read),
        read_at=n.read_at,
        resolved_at=getattr(n, "resolved_at", None),
        dismissed_at=getattr(n, "dismissed_at", None),
        created_at=n.created_at
    )


@router.get("", response_model=ApiSuccessResponse[PaginatedNotificationsResponse])
async def list_user_notifications(
    is_read: Optional[bool] = Query(None),
    notification_type: Optional[str] = Query(None, alias="type"),
    priority: Optional[str] = Query(None),
    requires_action: Optional[bool] = Query(None),
    action_status: Optional[str] = Query(None),
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
    if priority:
        filters.append(NotificationModel.priority == priority.upper())
    if requires_action is not None:
        filters.append(NotificationModel.requires_action == requires_action)
    if action_status:
        filters.append(NotificationModel.action_status == action_status.upper())

    # Total matching count
    count_query = select(func.count()).select_from(NotificationModel).where(*filters)
    total = (await db.execute(count_query)).scalar() or 0

    # Total unread count
    unread_query = select(func.count()).select_from(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_read == False
    )
    unread_count = (await db.execute(unread_query)).scalar() or 0

    # Total priority unread count
    prio_unread_query = select(func.count()).select_from(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_read == False,
        NotificationModel.priority.in_(["CRITICAL", "HIGH", "PRIORITY"])
    )
    priority_unread_count = (await db.execute(prio_unread_query)).scalar() or 0

    # Total open action-required count
    action_req_query = select(func.count()).select_from(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.requires_action == True,
        NotificationModel.action_status.in_(["OPEN", "ACKNOWLEDGED"])
    )
    action_required_count = (await db.execute(action_req_query)).scalar() or 0

    # Paginated results ordered by created_at DESC with outerjoin to HomeModel
    query = (
        select(NotificationModel, HomeModel.name)
        .outerjoin(HomeModel, NotificationModel.home_id == HomeModel.id)
        .where(*filters)
        .order_by(
            NotificationModel.created_at.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    dtos = [_to_dto(n, home_name) for n, home_name in rows]

    return ApiSuccessResponse(
        data=PaginatedNotificationsResponse(
            items=dtos,
            unread_count=unread_count,
            priority_unread_count=priority_unread_count,
            action_required_count=action_required_count,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/priority", response_model=ApiSuccessResponse[PriorityAlertSummaryDTO])
async def get_priority_alerts(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dedicated endpoint for the Header and Dashboard Priority Alert Banner.
    Returns all active unresolved action-required items, and unread CRITICAL/HIGH alerts.
    """
    # Active action-required items
    prio_filter = (
        (NotificationModel.user_id == current_user.id) &
        (
            (
                (NotificationModel.requires_action == True) &
                (NotificationModel.action_status.in_(["OPEN", "ACKNOWLEDGED"]))
            ) |
            (
                (NotificationModel.priority.in_(["CRITICAL", "HIGH"])) &
                (NotificationModel.is_read == False)
            )
        )
    )

    query = (
        select(NotificationModel, HomeModel.name)
        .outerjoin(HomeModel, NotificationModel.home_id == HomeModel.id)
        .where(prio_filter)
        .order_by(
            NotificationModel.created_at.desc()
        )
        .limit(20)
    )
    result = await db.execute(query)
    rows = result.all()
    dtos = [_to_dto(n, home_name) for n, home_name in rows]

    # Metrics
    crit_query = select(func.count()).select_from(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.priority == "CRITICAL",
        NotificationModel.action_status.in_(["OPEN", "ACKNOWLEDGED"])
    )
    critical_count = (await db.execute(crit_query)).scalar() or 0

    high_query = select(func.count()).select_from(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.priority == "HIGH",
        NotificationModel.action_status.in_(["OPEN", "ACKNOWLEDGED"])
    )
    high_count = (await db.execute(high_query)).scalar() or 0

    action_count = len([d for d in dtos if d.requires_action and d.action_status in ["OPEN", "ACKNOWLEDGED"]])
    unread_count = len([d for d in dtos if not d.is_read])

    return ApiSuccessResponse(
        data=PriorityAlertSummaryDTO(
            action_required_count=action_count,
            critical_count=critical_count,
            high_count=high_count,
            unread_count=unread_count,
            items=dtos
        )
    )


@router.patch("/{notification_id}/read", response_model=ApiSuccessResponse[MessageResponse])
async def mark_notification_read(
    notification_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks notification as read (read_at set).
    Invariant: Read ≠ Resolved. Reading does not change action_status.
    """
    success = await notification_service.mark_as_read(notification_id, current_user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")

    return ApiSuccessResponse(data=MessageResponse(message="Notification marked as read."))


@router.patch("/{notification_id}/acknowledge", response_model=ApiSuccessResponse[MessageResponse])
async def acknowledge_notification(
    notification_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks action-required notification as ACKNOWLEDGED.
    """
    success = await notification_service.acknowledge(notification_id, current_user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")

    return ApiSuccessResponse(data=MessageResponse(message="Notification acknowledged."))


@router.patch("/{notification_id}/resolve", response_model=ApiSuccessResponse[MessageResponse])
async def resolve_notification(
    notification_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Explicitly resolves an action-required notification.
    """
    success = await notification_service.resolve(notification_id, current_user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")

    return ApiSuccessResponse(data=MessageResponse(message="Notification marked as resolved."))


@router.patch("/{notification_id}/dismiss", response_model=ApiSuccessResponse[MessageResponse])
async def dismiss_notification(
    notification_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dismisses an action-required notification without resolving the underlying business event.
    """
    success = await notification_service.dismiss(notification_id, current_user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")

    return ApiSuccessResponse(data=MessageResponse(message="Notification dismissed."))


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
