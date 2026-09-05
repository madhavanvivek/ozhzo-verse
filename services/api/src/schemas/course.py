from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ==============================================================================
# Course Schemas
# ==============================================================================

class CourseSessionDTO(BaseModel):
    id: UUID
    course_id: UUID
    home_id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    location: Optional[str] = None
    recurrence_type: str = "NONE"
    status: str = "SCHEDULED"
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateCourseSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    location: Optional[str] = Field(None, max_length=200)
    recurrence_type: str = Field(default="NONE", pattern="^(NONE|DAILY|WEEKLY|MONTHLY)$")
    status: str = Field(default="SCHEDULED", pattern="^(SCHEDULED|ATTENDED|CANCELLED)$")
    notes: Optional[str] = Field(None, max_length=2000)


class UpdateCourseSessionRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    location: Optional[str] = Field(None, max_length=200)
    recurrence_type: Optional[str] = Field(None, pattern="^(NONE|DAILY|WEEKLY|MONTHLY)$")
    status: Optional[str] = Field(None, pattern="^(SCHEDULED|ATTENDED|CANCELLED)$")
    notes: Optional[str] = Field(None, max_length=2000)


class CourseAssignmentDTO(BaseModel):
    id: UUID
    course_id: UUID
    home_id: UUID
    title: str
    description: Optional[str] = None
    due_date: datetime
    status: str = "PENDING"
    assigned_to: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class CreateCourseAssignmentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    due_date: datetime
    status: str = Field(default="PENDING", pattern="^(PENDING|SUBMITTED|COMPLETED)$")
    assigned_to: Optional[UUID] = None


class UpdateCourseAssignmentRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(PENDING|SUBMITTED|COMPLETED)$")
    assigned_to: Optional[UUID] = None


class CourseExamDTO(BaseModel):
    id: UUID
    course_id: UUID
    home_id: UUID
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    status: str = "SCHEDULED"
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateCourseExamRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    status: str = Field(default="SCHEDULED", pattern="^(SCHEDULED|COMPLETED|MISSED)$")
    notes: Optional[str] = Field(None, max_length=2000)


class UpdateCourseExamRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, pattern="^(SCHEDULED|COMPLETED|MISSED)$")
    notes: Optional[str] = Field(None, max_length=2000)


class CourseDTO(BaseModel):
    id: UUID
    home_id: UUID
    title: str
    description: Optional[str] = None
    instructor: Optional[str] = None
    provider: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "ACTIVE"
    color: str = "#6366f1"
    created_at: datetime
    updated_at: datetime


class CourseDetailDTO(CourseDTO):
    sessions: List[CourseSessionDTO] = []
    assignments: List[CourseAssignmentDTO] = []
    exams: List[CourseExamDTO] = []


class CreateCourseRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    instructor: Optional[str] = Field(None, max_length=120)
    provider: Optional[str] = Field(None, max_length=120)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|COMPLETED|PAUSED|DROPPED)$")
    color: str = Field(default="#6366f1", max_length=20)


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    instructor: Optional[str] = Field(None, max_length=120)
    provider: Optional[str] = Field(None, max_length=120)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(ACTIVE|COMPLETED|PAUSED|DROPPED)$")
    color: Optional[str] = Field(None, max_length=20)


class PaginatedCoursesResponse(BaseModel):
    items: List[CourseDTO]
    total: int
    page: int
    page_size: int
    total_pages: int
