from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class SearchResultItemDTO(BaseModel):
    id: UUID
    domain: str  # INVENTORY, ASSET, LOCATION, PURCHASE, TASK, BILL, EVENT, MEMBER
    title: str
    subtitle: Optional[str] = None
    location_path: Optional[str] = None
    status: Optional[str] = None
    relevance: float = 1.0
    navigation_target: str
    meta_info: Optional[Dict[str, Any]] = None


class UnifiedSearchResponse(BaseModel):
    query: str
    total_results: int
    results_by_domain: Dict[str, int]
    items: List[SearchResultItemDTO] = []
