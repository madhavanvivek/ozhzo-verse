from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class AttentionItemDTO(BaseModel):
    id: UUID
    severity: Literal["CRITICAL", "HIGH", "NORMAL", "INFO"]
    category: str  # BILL_OVERDUE, TASK_OVERDUE, BILL_DUE_TODAY, TASK_DUE_TODAY, STOCK_EMPTY, STOCK_LOW, ASSET_OVERDUE, EVENT_TODAY, INVITATION_PENDING
    title: str
    subtitle: str
    action_label: str
    navigation_target: str
    meta_info: Optional[Dict[str, Any]] = None


class AttentionSummaryDTO(BaseModel):
    critical_count: int = 0
    high_count: int = 0
    normal_count: int = 0
    info_count: int = 0
    total_attention_items: int = 0


class AttentionCenterResponse(BaseModel):
    summary: AttentionSummaryDTO
    items: List[AttentionItemDTO] = []
