from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TodayTimelineItemDTO(BaseModel):
    id: UUID
    source_type: Literal["EVENT", "TASK", "BILL", "PURCHASE", "INVENTORY", "ASSET", "NOTIFICATION", "MEMBER"]
    source_id: UUID
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    priority: str = "NORMAL"  # CRITICAL, URGENT, HIGH, NORMAL, LOW
    status: str
    navigation_target: str
    category_name: Optional[str] = None
    location: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class TodayAttentionItemDTO(BaseModel):
    id: UUID
    source_type: Literal["TASK", "BILL", "EVENT", "INVENTORY", "PURCHASE", "ASSET", "NOTIFICATION", "MEMBER"]
    source_id: UUID
    title: str
    subtitle: Optional[str] = None
    priority: Literal["CRITICAL", "HIGH", "NORMAL", "LOW"] = "NORMAL"
    badge_text: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[datetime] = None
    navigation_target: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    category_name: Optional[str] = None
    assignee_id: Optional[UUID] = None
    assignee_name: Optional[str] = None
    is_assigned_to_me: bool = False
    location: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class TodayTasksSectionDTO(BaseModel):
    overdue: List[TodayAttentionItemDTO] = Field(default_factory=list)
    due_today: List[TodayAttentionItemDTO] = Field(default_factory=list)
    my_tasks: List[TodayAttentionItemDTO] = Field(default_factory=list)
    family_tasks: List[TodayAttentionItemDTO] = Field(default_factory=list)
    upcoming: List[TodayAttentionItemDTO] = Field(default_factory=list)
    completed_today_count: int = 0


class TodayBillsSectionDTO(BaseModel):
    overdue: List[TodayAttentionItemDTO] = Field(default_factory=list)
    due_today: List[TodayAttentionItemDTO] = Field(default_factory=list)
    upcoming: List[TodayAttentionItemDTO] = Field(default_factory=list)
    total_due_today_amount: float = 0.0
    currency: str = "USD"


class TodayCalendarSectionDTO(BaseModel):
    today_events: List[TodayAttentionItemDTO] = Field(default_factory=list)
    upcoming_events: List[TodayAttentionItemDTO] = Field(default_factory=list)


class TodayInventorySectionDTO(BaseModel):
    out_of_stock: List[TodayAttentionItemDTO] = Field(default_factory=list)
    low_stock: List[TodayAttentionItemDTO] = Field(default_factory=list)
    expiring_soon: List[TodayAttentionItemDTO] = Field(default_factory=list)


class TodayShoppingSectionDTO(BaseModel):
    urgent_items: List[TodayAttentionItemDTO] = Field(default_factory=list)
    pending_items: List[TodayAttentionItemDTO] = Field(default_factory=list)
    total_pending_count: int = 0


class TodayFamilySectionDTO(BaseModel):
    active_members_count: int = 0
    pending_invitations_count: int = 0
    member_workloads: List[Dict[str, Any]] = Field(default_factory=list)


class TodayNotificationsSectionDTO(BaseModel):
    unread_count: int = 0
    important_alerts: List[TodayAttentionItemDTO] = Field(default_factory=list)


class TodaySummaryDTO(BaseModel):
    total_items: int = 0
    critical_count: int = 0
    high_count: int = 0
    normal_count: int = 0
    low_count: int = 0
    events_count: int = 0
    tasks_count: int = 0
    bills_count: int = 0
    purchase_urgent_count: int = 0
    inventory_alerts_count: int = 0


class TodayResponseDTO(BaseModel):
    date: str
    timezone: str
    home_id: Optional[UUID] = None
    home_name: Optional[str] = None
    summary: TodaySummaryDTO
    needs_attention: List[TodayAttentionItemDTO] = Field(default_factory=list)
    timeline: List[TodayTimelineItemDTO] = Field(default_factory=list)
    attention_alerts: List[TodayTimelineItemDTO] = Field(default_factory=list)
    tasks: Optional[TodayTasksSectionDTO] = None
    bills: Optional[TodayBillsSectionDTO] = None
    calendar: Optional[TodayCalendarSectionDTO] = None
    inventory: Optional[TodayInventorySectionDTO] = None
    shopping: Optional[TodayShoppingSectionDTO] = None
    family: Optional[TodayFamilySectionDTO] = None
    notifications: Optional[TodayNotificationsSectionDTO] = None
