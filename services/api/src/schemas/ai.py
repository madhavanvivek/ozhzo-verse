from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class AIIntentType(str, Enum):
    # Tasks
    QUERY_TASKS = "QUERY_TASKS"
    CREATE_TASK = "CREATE_TASK"
    UPDATE_TASK = "UPDATE_TASK"
    COMPLETE_TASK = "COMPLETE_TASK"

    # Bills
    QUERY_BILLS = "QUERY_BILLS"
    CREATE_BILL = "CREATE_BILL"
    UPDATE_BILL = "UPDATE_BILL"

    # Calendar Events
    QUERY_EVENTS = "QUERY_EVENTS"
    CREATE_EVENT = "CREATE_EVENT"
    UPDATE_EVENT = "UPDATE_EVENT"

    # Shopping
    QUERY_SHOPPING = "QUERY_SHOPPING"
    ADD_SHOPPING_ITEM = "ADD_SHOPPING_ITEM"
    MARK_PURCHASED = "MARK_PURCHASED"

    # Inventory
    QUERY_INVENTORY = "QUERY_INVENTORY"
    ADD_INVENTORY_ITEM = "ADD_INVENTORY_ITEM"
    CONSUME_INVENTORY_ITEM = "CONSUME_INVENTORY_ITEM"
    RESTOCK_INVENTORY_ITEM = "RESTOCK_INVENTORY_ITEM"

    # Household & Administrative
    QUERY_MEMBERS = "QUERY_MEMBERS"
    QUERY_NOTIFICATIONS = "QUERY_NOTIFICATIONS"
    SUBSCRIPTION_STATUS = "SUBSCRIPTION_STATUS"
    GENERAL_HOUSEHOLD_QUERY = "GENERAL_HOUSEHOLD_QUERY"


class AIActionType(str, Enum):
    CREATE_TASK = "CREATE_TASK"
    COMPLETE_TASK = "COMPLETE_TASK"
    CREATE_BILL = "CREATE_BILL"
    CREATE_EVENT = "CREATE_EVENT"
    ADD_SHOPPING_ITEM = "ADD_SHOPPING_ITEM"
    ADD_INVENTORY_ITEM = "ADD_INVENTORY_ITEM"
    CONSUME_INVENTORY_ITEM = "CONSUME_INVENTORY_ITEM"
    RESTOCK_INVENTORY_ITEM = "RESTOCK_INVENTORY_ITEM"


class AIActionProposalDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique ID of the staged action proposal")
    action_type: AIActionType
    title: str = Field(..., description="Human-readable title of the proposed action")
    description: str = Field(..., description="Explanation of what will happen upon confirmation")
    params: Dict[str, Any] = Field(default_factory=dict, description="Structured parameters for domain execution")
    requires_confirmation: bool = Field(default=True, description="True for all state-mutating actions")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User natural language message or command")
    conversation_context: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Optional prior message history for multi-turn conversations"
    )


class AIChatResponse(BaseModel):
    message: str = Field(..., description="AI natural language response")
    detected_intent: AIIntentType = Field(..., description="Classified intent")
    intent_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    action_proposal: Optional[AIActionProposalDTO] = None
    data_payload: Optional[Dict[str, Any]] = None
    suggested_quick_replies: List[str] = Field(default_factory=list)


class AIActionConfirmRequest(BaseModel):
    action_id: str = Field(..., description="ID of the action proposal to confirm and execute")


class AIActionExecutionResult(BaseModel):
    success: bool
    action_id: str
    action_type: AIActionType
    executed_entity_id: Optional[str] = None
    message: str
    audit_log_id: Optional[str] = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class AIRecommendationDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    domain: str = Field(..., description="TASK, BILL, SHOPPING, INVENTORY, CALENDAR")
    priority: str = Field(default="NORMAL", description="LOW, NORMAL, HIGH, URGENT")
    title: str
    reason: str
    suggested_action: Optional[AIActionProposalDTO] = None


class AIUsageMetricsDTO(BaseModel):
    home_id: str
    total_interactions: int = 0
    total_actions_proposed: int = 0
    total_actions_executed: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
