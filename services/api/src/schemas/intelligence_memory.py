from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# ENUMS
# ==============================================================================

class MemoryCategory(str, Enum):
    PREFERENCE = "PREFERENCE"
    ROUTINE = "ROUTINE"
    HOUSEHOLD_PATTERN = "HOUSEHOLD_PATTERN"
    IMPORTANT_FACT = "IMPORTANT_FACT"
    RECURRING_BEHAVIOR = "RECURRING_BEHAVIOR"
    USER_INSTRUCTION = "USER_INSTRUCTION"
    DISMISSED_PREFERENCE = "DISMISSED_PREFERENCE"
    AUTOMATION_PREFERENCE = "AUTOMATION_PREFERENCE"


class MemorySource(str, Enum):
    USER_PROVIDED = "USER_PROVIDED"
    USER_CONFIRMED = "USER_CONFIRMED"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"
    AI_INFERRED = "AI_INFERRED"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


# ==============================================================================
# HOUSEHOLD MEMORY SCHEMAS
# ==============================================================================

class HouseholdMemoryCreateRequest(BaseModel):
    category: MemoryCategory
    content: str = Field(..., min_length=2, max_length=1000)
    source: MemorySource = MemorySource.USER_PROVIDED
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    context_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class HouseholdMemoryUpdateRequest(BaseModel):
    content: Optional[str] = Field(None, min_length=2, max_length=1000)
    category: Optional[MemoryCategory] = None
    status: Optional[MemoryStatus] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    context_metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class HouseholdMemoryResponseDTO(BaseModel):
    id: str
    home_id: str
    user_id: Optional[str] = None
    category: MemoryCategory
    content: str
    source: MemorySource
    confidence: float
    status: MemoryStatus
    context_metadata: Dict[str, Any] = Field(default_factory=dict)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# PERSONALIZATION PREFERENCES
# ==============================================================================

class PersonalizationPreferenceDTO(BaseModel):
    id: str
    user_id: str
    home_id: str
    personalization_enabled: bool
    ai_memory_enabled: bool
    reminder_timing_preference: str  # 1_DAY_BEFORE, SAME_DAY_MORNING, SAME_DAY_EVENING, 2_DAYS_BEFORE
    recommendation_frequency: str    # HIGH, BALANCED, LOW, MUTED
    digest_enabled: bool
    digest_day_of_week: str
    preferences_json: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class PersonalizationPreferenceUpdateRequest(BaseModel):
    personalization_enabled: Optional[bool] = None
    ai_memory_enabled: Optional[bool] = None
    reminder_timing_preference: Optional[str] = None
    recommendation_frequency: Optional[str] = None
    digest_enabled: Optional[bool] = None
    digest_day_of_week: Optional[str] = None
    preferences_json: Optional[Dict[str, Any]] = None


# ==============================================================================
# AI AGENT PLANNING & CONTINUITY
# ==============================================================================

class AIAgentPlanStepDTO(BaseModel):
    step_number: int
    action_type: str
    target_domain: str
    description: str
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    permission_required: str
    status: str = "PENDING"  # PENDING, CONFIRMED, EXECUTED, SKIPPED, FAILED
    result: Optional[Dict[str, Any]] = None


class AIAgentPlanDTO(BaseModel):
    plan_id: str
    title: str
    summary: str
    steps: List[AIAgentPlanStepDTO]
    requires_confirmation: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AIConversationTurnRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    session_token: Optional[str] = None


class AIConversationTurnResponse(BaseModel):
    session_token: str
    response_text: str
    suggested_plan: Optional[AIAgentPlanDTO] = None
    action_proposal: Optional[Dict[str, Any]] = None
    retrieved_memory_snippets: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False


# ==============================================================================
# HOUSEHOLD SUMMARY & DIGEST
# ==============================================================================

class HouseholdDigestDTO(BaseModel):
    home_id: str
    home_name: str
    period_start: datetime
    period_end: datetime
    tasks_completed_count: int
    tasks_overdue_count: int
    bills_paid_count: int
    bills_upcoming_count: int
    shopping_items_purchased_count: int
    inventory_low_count: int
    automations_executed_count: int
    highlights: List[str] = Field(default_factory=list)
    key_recommendations: List[str] = Field(default_factory=list)
