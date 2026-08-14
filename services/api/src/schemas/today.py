from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class TodayTimelineItemDTO(BaseModel):
    id: UUID
    source_type: Literal["EVENT", "TASK", "BILL", "PURCHASE", "INVENTORY", "ASSET"]
    source_id: UUID
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    priority: str = "NORMAL"  # URGENT, HIGH, NORMAL, LOW
    status: str
    navigation_target: str
    category_name: Optional[str] = None
    location: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class TodaySummaryDTO(BaseModel):
    total_items: int = 0
    events_count: int = 0
    tasks_count: int = 0
    bills_count: int = 0
    purchase_urgent_count: int = 0
    inventory_alerts_count: int = 0


class TodayResponseDTO(BaseModel):
    date: str
    timezone: str
    summary: TodaySummaryDTO
    timeline: List[TodayTimelineItemDTO] = []
    attention_alerts: List[TodayTimelineItemDTO] = []
