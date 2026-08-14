import abc
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
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
        home_id: UUID,
        user_id: UUID,
        title: str,
        body: str,
        type: str,
        metadata: Optional[dict] = None
    ):
        self.home_id = home_id
        self.user_id = user_id
        self.title = title
        self.body = body
        self.type = type
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
        record = NotificationModel(
            home_id=payload.home_id,
            user_id=payload.user_id,
            title=payload.title,
            body=payload.body,
            type=payload.type,
            is_read=False
        )
        db.add(record)
        await db.flush()

        if redis_client:
            try:
                event_data = {
                    "event": "NOTIFICATION_RECEIVED",
                    "id": str(record.id),
                    "title": record.title,
                    "body": record.body,
                    "type": record.type,
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
        return type_map.get(notification_type, True)

    async def dispatch(
        self,
        home_id: UUID,
        user_id: UUID,
        title: str,
        body: str,
        type: str,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        pref = await self.get_user_preferences(user_id, db)

        # 1. Check if user enabled this notification category
        if not self.is_type_enabled(type, pref):
            logger.info(f"Notification of type {type} suppressed by user preference for user {user_id}")
            return False

        payload = NotificationPayload(home_id, user_id, title, body, type, metadata)

        # 2. Dispatch to In-App channel
        if pref.in_app_enabled:
            await self.in_app_handler.send(payload, db, redis_client)

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


notification_service = NotificationService()
