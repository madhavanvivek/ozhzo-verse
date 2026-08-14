from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

from src.schemas.attention import AttentionItemDTO, AttentionSummaryDTO
from src.schemas.today import TodayTimelineItemDTO
from src.schemas.activity import HomeActivityItemDTO


class DashboardGreetingDTO(BaseModel):
    greeting: str
    user_display_name: str
    date_formatted: str
    time_period: str  # morning, afternoon, evening, night


class DashboardSummaryDTO(BaseModel):
    home_id: UUID
    home_name: str
    currency: str
    timezone: str
    members_count: int
    active_tasks_count: int
    low_stock_count: int
    unpaid_bills_count: int
    unpaid_bills_sum: Decimal
    purchase_items_count: int = 0
    borrowed_assets_count: int = 0
    upcoming_events_count: int
    unread_notifications_count: int


class DashboardTaskItemDTO(BaseModel):
    id: UUID
    title: str
    priority: str
    status: str
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[UUID] = None
    assigned_to_name: Optional[str] = None


class DashboardBillItemDTO(BaseModel):
    id: UUID
    title: str
    amount: Decimal
    currency: str
    due_date: date
    status: str


class DashboardEventItemDTO(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    location: Optional[str] = None


class DashboardInventoryItemDTO(BaseModel):
    id: UUID
    name: str
    quantity: Decimal
    unit: str
    status: str
    min_threshold: Optional[Decimal] = None


class DashboardShoppingItemDTO(BaseModel):
    id: UUID
    name: str
    quantity: Decimal
    unit: str
    is_checked: bool


class DashboardNotificationItemDTO(BaseModel):
    id: UUID
    title: str
    body: str
    type: str
    created_at: datetime


class DashboardResponseDTO(BaseModel):
    greeting: DashboardGreetingDTO
    summary: DashboardSummaryDTO
    attention_summary: Optional[AttentionSummaryDTO] = None
    attention_items: List[AttentionItemDTO] = []
    today_timeline: List[TodayTimelineItemDTO] = []
    recent_activity: List[HomeActivityItemDTO] = []
    pending_tasks: List[DashboardTaskItemDTO] = []
    upcoming_bills: List[DashboardBillItemDTO] = []
    upcoming_events: List[DashboardEventItemDTO] = []
    low_stock_inventory: List[DashboardInventoryItemDTO] = []
    shopping_items: List[DashboardShoppingItemDTO] = []
    notifications: List[DashboardNotificationItemDTO] = []
    role: str
