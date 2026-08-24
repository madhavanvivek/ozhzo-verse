from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any


class TaskCategoryDTO(BaseModel):
    id: UUID
    home_id: UUID
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateTaskCategoryRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = 0


class TaskTemplateDTO(BaseModel):
    id: UUID
    name: str
    default_category_name: str = "Maintenance"
    default_priority: str = "NORMAL"
    default_recurrence_type: str = "NONE"
    default_interval_days: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateTaskTemplateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    default_category_name: Optional[str] = "Maintenance"
    default_priority: Optional[str] = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH)$")
    default_recurrence_type: Optional[str] = Field(default="NONE", pattern="^(NONE|DAILY|WEEKLY|MONTHLY|YEARLY|CUSTOM_DAYS)$")
    default_interval_days: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0


class TaskDTO(BaseModel):
    id: UUID
    home_id: UUID
    template_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: str = "NORMAL"
    status: str = "TODO"
    due_date: Optional[datetime] = None
    is_overdue: bool = False
    is_due_today: bool = False
    recurrence_type: str = "NONE"
    recurrence_interval_days: Optional[int] = None
    recurrence_strategy: str = "SCHEDULED_DATE"
    parent_recurring_task_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    created_by: UUID
    created_by_name: Optional[str] = None
    completed_by: Optional[UUID] = None
    completed_by_name: Optional[str] = None
    completed_at: Optional[datetime] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime

    @property
    def recurrence_rule(self) -> str:
        return self.recurrence_type


class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Optional[str] = Field(default="NORMAL", pattern="^(LOW|NORMAL|MEDIUM|HIGH|URGENT)$")
    category_id: Optional[UUID] = None
    category: Optional[str] = None
    template_id: Optional[UUID] = None
    template: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    recurrence_type: Optional[str] = Field(default="NONE", pattern="^(NONE|DAILY|WEEKLY|MONTHLY|YEARLY|CUSTOM_DAYS)$")
    recurrence_rule: Optional[str] = None
    recurrence_interval_days: Optional[int] = None
    recurrence_strategy: Optional[str] = Field(default="SCHEDULED_DATE", pattern="^(SCHEDULED_DATE|COMPLETION_DATE)$")

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if ("recurrence_type" not in data or data.get("recurrence_type") is None) and "recurrence_rule" in data:
                data["recurrence_type"] = data["recurrence_rule"]
            if data.get("priority") == "MEDIUM":
                data["priority"] = "NORMAL"
        return data

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Task title must be at least 2 characters.")
        return cleaned


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(LOW|NORMAL|HIGH)$")
    status: Optional[str] = Field(None, pattern="^(TODO|IN_PROGRESS|COMPLETED|CANCELLED)$")
    category_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    recurrence_type: Optional[str] = Field(None, pattern="^(NONE|DAILY|WEEKLY|MONTHLY|YEARLY|CUSTOM_DAYS)$")
    recurrence_interval_days: Optional[int] = None
    recurrence_strategy: Optional[str] = Field(None, pattern="^(SCHEDULED_DATE|COMPLETION_DATE)$")
    version: Optional[int] = None


class CompleteTaskRequest(BaseModel):
    notes: Optional[str] = None
    version: Optional[int] = None


class AssignTaskRequest(BaseModel):
    assigned_to: Optional[UUID] = None


class TaskSummaryDTO(BaseModel):
    total_active: int
    due_today: int
    overdue: int
    upcoming: int
    my_tasks: int
    completed_history_count: int


class PaginatedTasksResponse(BaseModel):
    items: List[TaskDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
