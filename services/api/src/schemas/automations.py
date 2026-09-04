from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    SCHEDULE = "SCHEDULE"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_OVERDUE = "TASK_OVERDUE"
    BILL_APPROACHING = "BILL_APPROACHING"
    BILL_OVERDUE = "BILL_OVERDUE"
    INVENTORY_LOW = "INVENTORY_LOW"
    INVENTORY_OUT_OF_STOCK = "INVENTORY_OUT_OF_STOCK"
    SHOPPING_ITEM_ADDED = "SHOPPING_ITEM_ADDED"
    SHOPPING_ITEM_PURCHASED = "SHOPPING_ITEM_PURCHASED"
    EVENT_APPROACHING = "EVENT_APPROACHING"
    MEMBER_JOINED = "MEMBER_JOINED"


class ConditionOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    CONTAINS = "CONTAINS"
    EXISTS = "EXISTS"


class ActionType(str, Enum):
    CREATE_TASK = "CREATE_TASK"
    ASSIGN_TASK = "ASSIGN_TASK"
    ADD_SHOPPING_ITEM = "ADD_SHOPPING_ITEM"
    RESTOCK_INVENTORY = "RESTOCK_INVENTORY"
    CONSUME_INVENTORY = "CONSUME_INVENTORY"
    CREATE_NOTIFICATION = "CREATE_NOTIFICATION"
    CREATE_EVENT = "CREATE_EVENT"
    CREATE_RECOMMENDATION = "CREATE_RECOMMENDATION"


class AutomationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ConditionRuleSchema(BaseModel):
    field: str = Field(..., description="Target property or field to evaluate (e.g. quantity, priority, title)")
    op: ConditionOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Expected value or threshold")


class ConditionGroupSchema(BaseModel):
    operator: str = Field(default="AND", description="Logical operator: AND or OR")
    rules: List[ConditionRuleSchema] = Field(default_factory=list, description="List of condition rules")


class AutomationActionSchema(BaseModel):
    action_type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters matching domain execution contracts")


class ScheduleConfigSchema(BaseModel):
    cron: Optional[str] = Field(None, description="Standard cron expression (e.g. '0 9 * * 1')")
    interval_days: Optional[int] = Field(None, description="Interval in days")
    time_of_day: Optional[str] = Field(None, description="HH:MM string in home timezone")
    timezone: str = Field(default="Asia/Kolkata")


class AutomationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    enabled: bool = Field(default=True)
    trigger_type: TriggerType
    conditions: Optional[ConditionGroupSchema] = Field(default_factory=ConditionGroupSchema)
    actions: List[AutomationActionSchema] = Field(..., min_length=1)
    schedule: Optional[ScheduleConfigSchema] = None
    execution_policy: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"max_retries": 3, "retry_backoff_sec": 60})



class AutomationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    trigger_type: Optional[TriggerType] = None
    conditions: Optional[ConditionGroupSchema] = None
    actions: Optional[List[AutomationActionSchema]] = None
    schedule: Optional[ScheduleConfigSchema] = None
    execution_policy: Optional[Dict[str, Any]] = None
    status: Optional[AutomationStatus] = None


class AutomationResponseDTO(BaseModel):
    id: str
    home_id: str
    created_by: Optional[str] = None
    name: str
    description: Optional[str] = None
    enabled: bool
    trigger_type: TriggerType
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    schedule: Dict[str, Any]
    execution_policy: Dict[str, Any]
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    status: AutomationStatus
    failure_count: int = 0
    consecutive_failures: int = 0
    version: int = 1
    created_at: datetime
    updated_at: datetime


class AutomationExecutionResponseDTO(BaseModel):
    id: str
    automation_id: str
    home_id: str
    trigger_event: Dict[str, Any]
    evaluated_conditions: Dict[str, Any]
    actions_attempted: int
    actions_succeeded: int
    actions_failed: int
    duration_ms: int
    status: ExecutionStatus
    error_details: Optional[str] = None
    correlation_id: Optional[str] = None
    idempotency_key: str
    created_at: datetime


class RecommendationStatus(str, Enum):
    NEW = "NEW"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"


class HouseholdRecommendationDTO(BaseModel):
    id: str
    home_id: str
    domain: str
    title: str
    reason: str
    confidence: float
    source_category: str
    suggested_action: Optional[Dict[str, Any]] = None
    status: RecommendationStatus
    created_at: datetime
    expires_at: Optional[datetime] = None


class HouseholdIntelligenceDashboardDTO(BaseModel):
    home_id: str
    home_name: str
    active_automations_count: int
    total_automations_count: int
    recent_executions_count: int
    failed_automations_count: int
    active_automations: List[AutomationResponseDTO] = Field(default_factory=list)
    recent_executions: List[AutomationExecutionResponseDTO] = Field(default_factory=list)
    recommendations: List[HouseholdRecommendationDTO] = Field(default_factory=list)
    predicted_patterns: List[Dict[str, Any]] = Field(default_factory=list)


class AIAutomationProposalRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500, description="Natural language prompt, e.g. 'Whenever milk is low, add it to shopping list'")


class AIAutomationProposalResponse(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    trigger_type: TriggerType
    conditions: ConditionGroupSchema
    actions: List[AutomationActionSchema]
    schedule: Optional[ScheduleConfigSchema] = None
    explanation: str
    requires_confirmation: bool = True
