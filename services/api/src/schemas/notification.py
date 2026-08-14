from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class NotificationDTO(BaseModel):
    id: UUID
    home_id: UUID
    user_id: UUID
    title: str
    body: str
    type: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationPreferencesDTO(BaseModel):
    in_app_enabled: bool = True
    push_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    whatsapp_enabled: bool = False

    task_assigned_enabled: bool = True
    bill_reminder_enabled: bool = True
    low_stock_enabled: bool = True
    event_reminder_enabled: bool = True
    home_invitation_enabled: bool = True
    system_enabled: bool = True


class UpdateNotificationPreferencesRequest(BaseModel):
    in_app_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None

    task_assigned_enabled: Optional[bool] = None
    bill_reminder_enabled: Optional[bool] = None
    low_stock_enabled: Optional[bool] = None
    event_reminder_enabled: Optional[bool] = None
    home_invitation_enabled: Optional[bool] = None
    system_enabled: Optional[bool] = None


class PaginatedNotificationsResponse(BaseModel):
    items: List[NotificationDTO]
    unread_count: int
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
