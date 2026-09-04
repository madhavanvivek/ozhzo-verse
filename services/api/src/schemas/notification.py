from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class NotificationDTO(BaseModel):
    id: UUID
    home_id: Optional[UUID] = None
    home_name: Optional[str] = None
    user_id: UUID
    title: str
    body: str
    type: str
    priority: str = "NORMAL"  # CRITICAL, HIGH, NORMAL, LOW
    requires_action: bool = False
    action_status: str = "OPEN"  # OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED
    action_type: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    is_read: bool
    read_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime


class PriorityAlertSummaryDTO(BaseModel):
    action_required_count: int
    critical_count: int
    high_count: int
    unread_count: int
    items: List[NotificationDTO]


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
    priority_unread_count: int = 0
    action_required_count: int = 0
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
