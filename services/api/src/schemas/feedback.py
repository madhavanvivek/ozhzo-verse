from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CreateFeedbackRequest(BaseModel):
    category: Literal["FEEDBACK", "BUG", "FEATURE_REQUEST"] = "FEEDBACK"
    message: str = Field(..., min_length=3, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    app_version: str = "0.1.0-pilot.1"


class FeedbackDTO(BaseModel):
    id: UUID
    home_id: Optional[UUID] = None
    user_id: UUID
    user_name: str
    category: str
    message: str
    rating: Optional[int] = None
    app_version: str
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: List[FeedbackDTO] = []
    total: int = 0
