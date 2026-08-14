from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class PurchaseItemDTO(BaseModel):
    id: UUID
    home_id: UUID
    inventory_item_id: Optional[UUID] = None
    name: str
    quantity: Decimal
    unit: str = "pcs"
    notes: Optional[str] = None
    status: str = "PENDING"  # PENDING, PURCHASED, CANCELLED
    added_by: Optional[UUID] = None
    added_by_name: Optional[str] = None
    purchased_by: Optional[UUID] = None
    purchased_by_name: Optional[str] = None
    purchased_at: Optional[datetime] = None
    restocked_to_inventory: bool = False
    version: int = 1
    created_at: datetime
    updated_at: datetime


class CreatePurchaseItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    quantity: Decimal = Field(default=Decimal("1.000"), gt=0)
    unit: str = Field(default="pcs", max_length=32)
    notes: Optional[str] = Field(None, max_length=1000)
    inventory_item_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Item name cannot be empty.")
        return cleaned


class UpdatePurchaseItemRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=32)
    notes: Optional[str] = Field(None, max_length=1000)
    version: Optional[int] = Field(None, ge=1)


class PurchaseActionRequest(BaseModel):
    restock_inventory: bool = Field(default=True)
    purchased_quantity: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=1000)


class PurchaseHistoryDTO(BaseModel):
    id: UUID
    home_id: UUID
    purchase_item_id: Optional[UUID] = None
    inventory_item_id: Optional[UUID] = None
    stock_movement_id: Optional[UUID] = None
    name: str
    quantity: Decimal
    unit: str = "pcs"
    purchased_by: Optional[UUID] = None
    purchased_by_name: Optional[str] = None
    purchased_at: datetime
    restocked_to_inventory: bool = False
    notes: Optional[str] = None
    created_at: datetime


class PurchaseSummaryDTO(BaseModel):
    total_pending: int = 0
    total_purchased_today: int = 0
    total_history_count: int = 0
    low_stock_suggestions_count: int = 0
