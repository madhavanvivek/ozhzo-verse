from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ShoppingListDTO(BaseModel):
    id: UUID
    home_id: UUID
    name: str
    total_items: int = 0
    checked_items: int = 0
    created_at: datetime
    updated_at: datetime


class CreateShoppingListRequest(BaseModel):
    name: str = Field(default="Main Shopping List", min_length=1, max_length=120)


class ShoppingListItemDTO(BaseModel):
    id: UUID
    list_id: UUID
    home_id: UUID
    inventory_item_id: Optional[UUID] = None
    name: str
    quantity: Decimal
    unit: str
    priority: str
    is_checked: bool
    added_by: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime


class CreateShoppingItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    quantity: Decimal = Field(default=Decimal("1.0"), ge=0)
    unit: str = Field(default="pcs", max_length=32)
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    assigned_to: Optional[UUID] = None
    inventory_item_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Item name cannot be empty.")
        return cleaned


class UpdateShoppingItemRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=32)
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    assigned_to: Optional[UUID] = None
    is_checked: Optional[bool] = None
    version: Optional[int] = None


class CheckItemRequest(BaseModel):
    is_checked: bool
    version: Optional[int] = None


class ConvertFromInventoryRequest(BaseModel):
    target_list_id: Optional[UUID] = None
    quantity: Optional[Decimal] = Field(None, gt=0)


class MessageResponse(BaseModel):
    message: str
