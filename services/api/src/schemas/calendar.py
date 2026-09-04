from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class EventCategoryDTO(BaseModel):
    id: UUID
    home_id: UUID
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateEventCategoryRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: Optional[int] = 0


class EventParticipantDTO(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: Optional[str] = None
    status: Literal["INVITED", "ACCEPTED", "DECLINED"] = "INVITED"
    created_at: Optional[datetime] = None


class EventDTO(BaseModel):
    id: UUID
    home_id: UUID
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    recurrence_type: Literal["NONE", "DAILY", "WEEKLY", "MONTHLY", "YEARLY", "CUSTOM_DAYS"] = "NONE"
    recurrence_interval_days: Optional[int] = None
    parent_recurring_event_id: Optional[UUID] = None
    status: Literal["CONFIRMED", "TENTATIVE", "CANCELLED"] = "CONFIRMED"
    reminder_minutes_before: Optional[int] = 30
    version: int = 1
    created_by: UUID
    created_by_name: Optional[str] = None
    participants: List[EventParticipantDTO] = []
    created_at: datetime
    updated_at: datetime


class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    location: Optional[str] = Field(None, max_length=255)
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    category_id: Optional[UUID] = None
    category_name: Optional[str] = Field(None, max_length=100)
    recurrence_type: Optional[Literal["NONE", "DAILY", "WEEKLY", "MONTHLY", "YEARLY", "CUSTOM_DAYS"]] = "NONE"
    recurrence_interval_days: Optional[int] = None
    reminder_minutes_before: Optional[int] = Field(default=30, ge=0)
    participant_user_ids: List[UUID] = []

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start and v < start:
            raise ValueError("Event end time cannot precede start time.")
        return v


class UpdateEventRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    category_id: Optional[UUID] = None
    category_name: Optional[str] = Field(None, max_length=100)
    recurrence_type: Optional[Literal["NONE", "DAILY", "WEEKLY", "MONTHLY", "YEARLY", "CUSTOM_DAYS"]] = None
    recurrence_interval_days: Optional[int] = None
    status: Optional[Literal["CONFIRMED", "TENTATIVE", "CANCELLED"]] = None
    reminder_minutes_before: Optional[int] = None
    participant_user_ids: Optional[List[UUID]] = None
    version: Optional[int] = None

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v: Optional[datetime], info) -> Optional[datetime]:
        start = info.data.get("start_time")
        if start and v and v < start:
            raise ValueError("Event end time cannot precede start time.")
        return v


class UpdateParticipantStatusRequest(BaseModel):
    status: Literal["ACCEPTED", "DECLINED"]


class TimelineItemDTO(BaseModel):
    source_type: Literal["EVENT", "TASK", "BILL"]
    source_id: UUID
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    editable: bool = True
    navigation_target: str
    status: str
    category_name: Optional[str] = None
    location: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class CalendarProjectionResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    items: List[TimelineItemDTO] = []
    timeline_items: Optional[List[TimelineItemDTO]] = None
    total_events: int = 0
    total_tasks: int = 0
    total_bills: int = 0


class MessageResponse(BaseModel):
    message: str
