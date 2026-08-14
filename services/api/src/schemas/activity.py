from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class HomeActivityItemDTO(BaseModel):
    id: UUID
    activity_type: str  # STOCK_MOVE, LOCATION_MOVE, TASK_COMPLETED, BILL_PAID, PURCHASE_CHECKED, ASSET_LOANED, EVENT_CREATED
    title: str
    description: str
    actor_id: Optional[UUID] = None
    actor_name: str
    timestamp: datetime
    time_ago: str
    navigation_target: str
    meta_info: Optional[Dict[str, Any]] = None


class HomeActivityResponseDTO(BaseModel):
    items: List[HomeActivityItemDTO] = []
    total: int = 0
