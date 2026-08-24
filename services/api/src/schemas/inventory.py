from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# Global Templates & Units Schemas
# ==============================================================================

class InventoryTemplateDTO(BaseModel):
    id: UUID
    name: str
    default_category_name: str = "Pantry"
    default_unit: str = "kg"
    description: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateInventoryTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    default_category_name: str = Field(default="Pantry", max_length=100)
    default_unit: str = Field(default="kg", max_length=32)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)


class UpdateInventoryTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    default_category_name: Optional[str] = Field(None, max_length=100)
    default_unit: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class UnitDTO(BaseModel):
    id: UUID
    home_id: Optional[UUID] = None
    name: str
    symbol: str
    measurement_type: str = "COUNT"  # WEIGHT, VOLUME, COUNT, LENGTH, OTHER
    is_active: bool = True
    is_global: bool = False
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateUnitRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    symbol: str = Field(..., min_length=1, max_length=32)
    measurement_type: str = Field(default="COUNT", max_length=32)
    sort_order: int = Field(default=0, ge=0)


class UpdateUnitRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    symbol: Optional[str] = Field(None, min_length=1, max_length=32)
    measurement_type: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


# ==============================================================================
# Categories & Locations Schemas
# ==============================================================================

class InventoryCategoryDTO(BaseModel):
    id: UUID
    home_id: UUID
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: int = Field(default=0, ge=0)


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: Optional[int] = Field(None, ge=0)


class LocationDTO(BaseModel):
    id: UUID
    home_id: UUID
    parent_id: Optional[UUID] = None
    name: str
    location_type: str = "ZONE"
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    path: Optional[str] = None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class LocationTreeDTO(LocationDTO):
    children: List["LocationTreeDTO"] = []


class LocationTypeDTO(BaseModel):
    id: Optional[UUID] = None
    home_id: Optional[UUID] = None
    name: str
    code: str
    description: Optional[str] = None
    icon: Optional[str] = None
    is_system_default: bool = False
    created_at: Optional[datetime] = None


class CreateLocationTypeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)


class CreateLocationRequest(BaseModel):
    parent_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=120)
    location_type: str = Field(default="ZONE", max_length=64)
    description: Optional[str] = Field(None, max_length=1000)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = Field(default=0, ge=0)


class UpdateLocationRequest(BaseModel):
    parent_id: Optional[UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    location_type: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=1000)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ConsumeStockRequest(BaseModel):
    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class RestockStockRequest(BaseModel):
    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)


# ==============================================================================
# Items & Assets Schemas
# ==============================================================================

class InventoryItemDTO(BaseModel):
    id: UUID
    home_id: UUID
    template_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    location_id: Optional[UUID] = None
    location_path: Optional[str] = None
    item_type: str = "CONSUMABLE"  # CONSUMABLE, ASSET
    name: str
    description: Optional[str] = None
    quantity: Decimal
    unit: str = "pcs"
    min_threshold: Optional[Decimal] = None
    preferred_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    condition: Optional[str] = None
    asset_status: str = "AVAILABLE"  # AVAILABLE, BORROWED, MISSING, ARCHIVED
    current_holder_name: Optional[str] = None
    current_holder_user_id: Optional[UUID] = None
    last_seen_at: Optional[datetime] = None
    last_seen_by: Optional[UUID] = None
    last_seen_location_id: Optional[UUID] = None
    expiry_date: Optional[date] = None
    status: str = "GOOD"  # GOOD, LOW, OUT_OF_STOCK
    expiry_status: str = "NORMAL"  # NORMAL, EXPIRING_SOON, EXPIRED
    notes: Optional[str] = None

    # Extended Asset Tracking & Home Memory
    brand: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    qr_code_identifier: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    purchase_store: Optional[str] = None
    warranty_expiry_date: Optional[date] = None
    warranty_status: Optional[str] = "NO_WARRANTY"  # ACTIVE, EXPIRING_SOON, EXPIRED, NO_WARRANTY
    warranty_notes: Optional[str] = None
    photo_url: Optional[str] = None
    receipt_url: Optional[str] = None
    manual_url: Optional[str] = None
    last_serviced_at: Optional[date] = None
    next_service_due_at: Optional[date] = None
    service_notes: Optional[str] = None

    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class CreateInventoryItemRequest(BaseModel):
    template_id: Optional[UUID] = None
    item_type: str = Field(default="CONSUMABLE", pattern="^(CONSUMABLE|ASSET)$")
    category_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    quantity: Decimal = Field(default=Decimal("1.000"), ge=0)
    unit: str = Field(default="pcs", max_length=32)
    min_threshold: Optional[Decimal] = Field(default=Decimal("1.000"), ge=0)
    preferred_quantity: Optional[Decimal] = Field(None, ge=0)
    max_quantity: Optional[Decimal] = Field(None, ge=0)
    condition: Optional[str] = Field(None, max_length=32)
    expiry_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)

    # Extended Asset Tracking & Home Memory
    brand: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=120)
    barcode: Optional[str] = Field(None, max_length=100)
    qr_code_identifier: Optional[str] = Field(None, max_length=120)
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    purchase_store: Optional[str] = Field(None, max_length=150)
    warranty_expiry_date: Optional[date] = None
    warranty_notes: Optional[str] = Field(None, max_length=1000)
    photo_url: Optional[str] = Field(None, max_length=512)
    receipt_url: Optional[str] = Field(None, max_length=512)
    manual_url: Optional[str] = Field(None, max_length=512)
    last_serviced_at: Optional[date] = None
    next_service_due_at: Optional[date] = None
    service_notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Item name cannot be empty.")
        return cleaned


class UpdateInventoryItemRequest(BaseModel):
    template_id: Optional[UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    category_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    description: Optional[str] = Field(None, max_length=1000)
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=32)
    min_threshold: Optional[Decimal] = Field(None, ge=0)
    preferred_quantity: Optional[Decimal] = Field(None, ge=0)
    max_quantity: Optional[Decimal] = Field(None, ge=0)
    condition: Optional[str] = Field(None, max_length=32)
    expiry_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)

    # Extended Asset Tracking & Home Memory
    brand: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=120)
    barcode: Optional[str] = Field(None, max_length=100)
    qr_code_identifier: Optional[str] = Field(None, max_length=120)
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    purchase_store: Optional[str] = Field(None, max_length=150)
    warranty_expiry_date: Optional[date] = None
    warranty_notes: Optional[str] = Field(None, max_length=1000)
    photo_url: Optional[str] = Field(None, max_length=512)
    receipt_url: Optional[str] = Field(None, max_length=512)
    manual_url: Optional[str] = Field(None, max_length=512)
    last_serviced_at: Optional[date] = None
    next_service_due_at: Optional[date] = None
    service_notes: Optional[str] = Field(None, max_length=1000)


class QRLabelResponse(BaseModel):
    item_id: UUID
    home_id: UUID
    item_name: str
    item_type: str
    location_path: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    qr_payload: str
    generated_at: datetime


# ==============================================================================
# Stock Movements Schemas
# ==============================================================================

class StockMovementRequest(BaseModel):
    movement_type: str = Field(..., pattern="^(ADD|CONSUME|ADJUST|PURCHASE|WASTE|RETURN)$")
    quantity: Decimal = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)


class StockMovementDTO(BaseModel):
    id: UUID
    home_id: UUID
    item_id: UUID
    movement_type: str
    quantity_delta: Decimal
    previous_quantity: Decimal
    resulting_quantity: Decimal
    reason: Optional[str] = None
    performed_by: Optional[UUID] = None
    created_at: datetime


# ==============================================================================
# Location Movements Schemas
# ==============================================================================

class MoveItemRequest(BaseModel):
    to_location_id: UUID
    reason: Optional[str] = Field(None, max_length=500)


class LocationMovementDTO(BaseModel):
    id: UUID
    home_id: UUID
    item_id: UUID
    from_location_id: Optional[UUID] = None
    to_location_id: UUID
    from_location_path: Optional[str] = None
    to_location_path: str
    reason: Optional[str] = None
    moved_by: Optional[UUID] = None
    moved_at: datetime


# ==============================================================================
# Asset Lending / Borrowing Schemas
# ==============================================================================

class BorrowItemRequest(BaseModel):
    borrower_name: str = Field(..., min_length=1, max_length=120)
    borrower_type: str = Field(default="MEMBER", pattern="^(MEMBER|EXTERNAL_PERSON|CONNECTED_HOME)$")
    borrower_user_id: Optional[UUID] = None
    borrower_contact: Optional[str] = Field(None, max_length=100)
    expected_return_at: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)


class ReturnItemRequest(BaseModel):
    return_location_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class AssetLoanDTO(BaseModel):
    id: UUID
    home_id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    borrower_type: str
    borrower_user_id: Optional[UUID] = None
    borrower_name: str
    borrower_contact: Optional[str] = None
    loan_status: str  # ACTIVE, RETURNED, OVERDUE, LOST
    borrowed_at: datetime
    expected_return_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    return_location_id: Optional[UUID] = None
    return_location_path: Optional[str] = None
    issued_by: Optional[UUID] = None
    received_by: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# Aggregates & Common
# ==============================================================================

class InventorySummaryDTO(BaseModel):
    total_items: int = 0
    consumables_count: int = 0
    assets_count: int = 0
    good_stock_count: int = 0
    low_stock_count: int = 0
    out_of_stock_count: int = 0
    expired_count: int = 0
    expiring_soon_count: int = 0
    borrowed_assets_count: int = 0


class PaginatedInventoryResponse(BaseModel):
    items: List[InventoryItemDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
