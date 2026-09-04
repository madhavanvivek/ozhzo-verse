import abc
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.infrastructure.database.models import (
    NotificationModel,
    UserNotificationPreferencesModel
)

logger = logging.getLogger("ozhzo.notifications")


class NotificationPayload:
    def __init__(
        self,
        user_id: UUID,
        title: str,
        body: str,
        type: str,
        home_id: Optional[UUID] = None,
        priority: str = "NORMAL",
        requires_action: Optional[bool] = None,
        action_type: Optional[str] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        dedup_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.home_id = home_id
        self.title = title
        self.body = body
        self.type = type
        self.priority = priority.upper() if priority else "NORMAL"

        # Determine if action is required automatically if not explicitly given
        if requires_action is not None:
            self.requires_action = bool(requires_action)
        else:
            self.requires_action = self.priority in ["CRITICAL", "HIGH"] or bool(action_type) or (
                type in [
                    "HOME_INVITATION",
                    "JOIN_REQUEST_RECEIVED",
                    "PAYMENT_FAILED",
                    "ACCESS_EXPIRING",
                    "ACCESS_EXPIRED",
                    "SUBSCRIPTION_EXPIRING",
                    "SUBSCRIPTION_EXPIRED"
                ]
            )

        self.action_type = action_type
        self.action_url = action_url
        self.action_label = action_label
        self.dedup_key = dedup_key
        self.metadata = metadata or {}


class BaseChannelHandler(abc.ABC):
    @abc.abstractmethod
    async def send(
        self,
        payload: NotificationPayload,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None
    ) -> bool:
        pass


class InAppChannelHandler(BaseChannelHandler):
    async def send(
        self,
        payload: NotificationPayload,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None
    ) -> bool:
        # 1. Deduplication check
        if payload.dedup_key:
            existing = await db.execute(
                select(NotificationModel.id).where(NotificationModel.dedup_key == payload.dedup_key)
            )
            if existing.scalars().first() if hasattr(existing, "scalars") else existing.first():
                logger.info(f"Duplicate notification suppressed by dedup_key: {payload.dedup_key}")
                return False

        meta_json = json.dumps(payload.metadata) if payload.metadata else None

        record = NotificationModel(
            home_id=payload.home_id,
            user_id=payload.user_id,
            title=payload.title,
            body=payload.body,
            type=payload.type,
            priority=payload.priority,
            requires_action=payload.requires_action,
            action_status="OPEN",
            action_type=payload.action_type,
            action_url=payload.action_url,
            action_label=payload.action_label,
            dedup_key=payload.dedup_key,
            extra_metadata=meta_json,
            is_read=False
        )
        db.add(record)
        await db.flush()

        if redis_client:
            try:
                event_data = {
                    "event": "NOTIFICATION_RECEIVED",
                    "id": str(record.id),
                    "home_id": str(record.home_id) if record.home_id else None,
                    "title": record.title,
                    "body": record.body,
                    "type": record.type,
                    "priority": record.priority,
                    "requires_action": record.requires_action,
                    "action_status": record.action_status,
                    "action_url": record.action_url,
                    "action_label": record.action_label,
                    "extra_metadata": payload.metadata,
                    "created_at": record.created_at.isoformat()
                }
                await redis_client.publish(
                    f"user:{payload.user_id}:notifications",
                    json.dumps(event_data)
                )
            except Exception as e:
                logger.warning(f"Failed to publish notification to Redis: {e}")

        return True


class PushChannelHandler(BaseChannelHandler):
    """Extensible APNs / FCM Push Notification Channel Adapter"""
    async def send(self, payload: NotificationPayload, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> bool:
        logger.info(f"[Push Adapter] Queued push notification for user {payload.user_id}: {payload.title}")
        return True


class EmailChannelHandler(BaseChannelHandler):
    """Extensible Transactional Email Channel Adapter (e.g. Resend / SendGrid)"""
    async def send(self, payload: NotificationPayload, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> bool:
        logger.info(f"[Email Adapter] Queued email notification for user {payload.user_id}: {payload.title}")
        return True


class SmsChannelHandler(BaseChannelHandler):
    """Extensible SMS Channel Adapter (e.g. Twilio / SNS)"""
    async def send(self, payload: NotificationPayload, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> bool:
        logger.info(f"[SMS Adapter] Queued SMS notification for user {payload.user_id}: {payload.title}")
        return True


class WhatsAppChannelHandler(BaseChannelHandler):
    """Extensible WhatsApp Business API Channel Adapter"""
    async def send(self, payload: NotificationPayload, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> bool:
        logger.info(f"[WhatsApp Adapter] Queued WhatsApp notification for user {payload.user_id}: {payload.title}")
        return True


class NotificationService:
    def __init__(self):
        self.in_app_handler = InAppChannelHandler()
        self.push_handler = PushChannelHandler()
        self.email_handler = EmailChannelHandler()
        self.sms_handler = SmsChannelHandler()
        self.whatsapp_handler = WhatsAppChannelHandler()

    async def get_user_preferences(self, user_id: UUID, db: AsyncSession) -> UserNotificationPreferencesModel:
        res = await db.execute(
            select(UserNotificationPreferencesModel).where(UserNotificationPreferencesModel.user_id == user_id)
        )
        pref = res.scalar_one_or_none()
        if not pref:
            pref = UserNotificationPreferencesModel(user_id=user_id)
            db.add(pref)
            await db.flush()
        return pref

    def is_type_enabled(self, notification_type: str, pref: UserNotificationPreferencesModel) -> bool:
        type_map = {
            "TASK_ASSIGNED": pref.task_assigned_enabled,
            "BILL_REMINDER": pref.bill_reminder_enabled,
            "LOW_STOCK": pref.low_stock_enabled,
            "EVENT_REMINDER": pref.event_reminder_enabled,
            "HOME_INVITATION": pref.home_invitation_enabled,
            "SYSTEM": pref.system_enabled,
        }
        val = type_map.get(notification_type, True)
        return True if val is None else bool(val)

    async def dispatch(
        self,
        home_id: Optional[UUID],
        user_id: UUID,
        title: str,
        body: str,
        type: str,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        priority: str = "NORMAL",
        requires_action: Optional[bool] = None,
        action_type: Optional[str] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        dedup_key: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        pref = await self.get_user_preferences(user_id, db)

        # 1. Check if user enabled this notification category (critical & security notifications bypass preference)
        if priority.upper() not in ["CRITICAL", "HIGH"] and not self.is_type_enabled(type, pref):
            logger.info(f"Notification of type {type} suppressed by user preference for user {user_id}")
            return False

        payload = NotificationPayload(
            user_id=user_id,
            home_id=home_id,
            title=title,
            body=body,
            type=type,
            priority=priority,
            requires_action=requires_action,
            action_type=action_type,
            action_url=action_url,
            action_label=action_label,
            dedup_key=dedup_key,
            metadata=metadata
        )

        # 2. Dispatch to In-App channel
        dispatched = True
        if pref.in_app_enabled:
            dispatched = await self.in_app_handler.send(payload, db, redis_client)

        if not dispatched:
            return False

        # 3. Channel gates (prepared for future multi-channel backends)
        if pref.push_enabled:
            await self.push_handler.send(payload, db, redis_client)
        if pref.email_enabled:
            await self.email_handler.send(payload, db, redis_client)
        if pref.sms_enabled:
            await self.sms_handler.send(payload, db, redis_client)
        if pref.whatsapp_enabled:
            await self.whatsapp_handler.send(payload, db, redis_client)

        return True

    async def dispatch_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: str,
        body: str,
        notification_type: Optional[str] = None,
        type: Optional[str] = None,
        home_id: Optional[UUID] = None,
        priority: str = "NORMAL",
        requires_action: Optional[bool] = None,
        action_type: Optional[str] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        dedup_key: Optional[str] = None,
        metadata: Optional[dict] = None,
        redis_client: Optional[redis.Redis] = None
    ) -> bool:
        eff_type = notification_type or type or "SYSTEM"
        return await self.dispatch(
            home_id=home_id,
            user_id=user_id,
            title=title,
            body=body,
            type=eff_type,
            db=db,
            redis_client=redis_client,
            priority=priority,
            requires_action=requires_action,
            action_type=action_type,
            action_url=action_url,
            action_label=action_label,
            dedup_key=dedup_key,
            metadata=metadata
        )

    async def mark_as_read(self, notification_id: UUID, user_id: UUID, db: AsyncSession) -> bool:
        res = await db.execute(
            select(NotificationModel).where(
                NotificationModel.id == notification_id,
                NotificationModel.user_id == user_id
            )
        )
        notif = res.scalar_one_or_none()
        if notif:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        return False

    async def mark_all_as_read(self, user_id: UUID, db: AsyncSession) -> int:
        query = (
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read == False
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        res = await db.execute(query)
        await db.commit()
        return res.rowcount

    async def acknowledge(self, notification_id: UUID, user_id: UUID, db: AsyncSession) -> bool:
        res = await db.execute(
            select(NotificationModel).where(
                NotificationModel.id == notification_id,
                NotificationModel.user_id == user_id
            )
        )
        notif = res.scalar_one_or_none()
        if notif:
            notif.action_status = "ACKNOWLEDGED"
            notif.is_read = True
            if not notif.read_at:
                notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        return False

    async def resolve(self, notification_id: UUID, user_id: UUID, db: AsyncSession) -> bool:
        res = await db.execute(
            select(NotificationModel).where(
                NotificationModel.id == notification_id,
                NotificationModel.user_id == user_id
            )
        )
        notif = res.scalar_one_or_none()
        if notif:
            notif.action_status = "RESOLVED"
            notif.resolved_at = datetime.now(timezone.utc)
            notif.is_read = True
            if not notif.read_at:
                notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        return False

    async def dismiss(self, notification_id: UUID, user_id: UUID, db: AsyncSession) -> bool:
        res = await db.execute(
            select(NotificationModel).where(
                NotificationModel.id == notification_id,
                NotificationModel.user_id == user_id
            )
        )
        notif = res.scalar_one_or_none()
        if notif:
            notif.action_status = "DISMISSED"
            notif.dismissed_at = datetime.now(timezone.utc)
            notif.is_read = True
            if not notif.read_at:
                notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        return False

    async def resolve_by_dedup_prefix(self, dedup_prefix: str, db: AsyncSession) -> int:
        try:
            query = (
                update(NotificationModel)
                .where(
                    NotificationModel.dedup_key.like(f"{dedup_prefix}%"),
                    NotificationModel.action_status == "OPEN"
                )
                .values(
                    action_status="RESOLVED",
                    resolved_at=datetime.now(timezone.utc)
                )
            )
            res = await db.execute(query)
            if hasattr(db, "commit") and callable(db.commit):
                await db.commit()
            return getattr(res, "rowcount", 0) or 0
        except Exception as e:
            logger.warning(f"resolve_by_dedup_prefix exception: {e}")
            return 0


notification_service = NotificationService()
