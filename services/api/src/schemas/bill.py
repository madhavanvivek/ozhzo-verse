from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any


class BillCategoryDTO(BaseModel):
    id: UUID
    home_id: UUID
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateBillCategoryRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = 0

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Category name must be at least 2 characters.")
        return cleaned


class BillTemplateDTO(BaseModel):
    id: UUID
    name: str
    default_category_name: str = "Utilities"
    default_recurrence_type: str = "MONTHLY"
    default_interval_days: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class CreateBillTemplateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    default_category_name: Optional[str] = "Utilities"
    default_recurrence_type: Optional[str] = Field(default="MONTHLY", pattern="^(NONE|MONTHLY|QUARTERLY|HALF_YEARLY|YEARLY|CUSTOM_DAYS)$")
    default_interval_days: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0


class BillPaymentDTO(BaseModel):
    id: UUID
    home_id: UUID
    bill_id: UUID
    amount_paid: Decimal
    currency: str = "INR"
    paid_date: date
    paid_by: UUID
    paid_by_name: Optional[str] = None
    payment_method: str = "UPI"
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class BillDTO(BaseModel):
    id: UUID
    home_id: UUID
    template_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    title: str
    expected_amount: Decimal
    currency: str = "INR"
    due_date: date
    is_overdue: bool = False
    is_due_today: bool = False
    recurrence_type: str = "NONE"
    recurrence_interval_days: Optional[int] = None
    recurrence_strategy: str = "SCHEDULED_DATE"
    parent_recurring_bill_id: Optional[UUID] = None
    status: str = "UNPAID"
    amount_paid: Decimal = Decimal("0.00")
    remaining_balance: Decimal = Decimal("0.00")
    responsible_member_id: Optional[UUID] = None
    responsible_member_name: Optional[str] = None
    notes: Optional[str] = None
    version: int = 1
    created_by: UUID
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @property
    def amount(self) -> Decimal:
        return self.expected_amount

    @property
    def recurrence_interval(self) -> str:
        return self.recurrence_type


class BillDetailDTO(BillDTO):
    payments: List[BillPaymentDTO] = []


class CreateBillRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    expected_amount: Optional[Decimal] = Field(None, gt=0)
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(default="INR", min_length=3, max_length=3)
    due_date: date
    recurrence_type: Optional[str] = Field(default="NONE", pattern="^(NONE|MONTHLY|QUARTERLY|HALF_YEARLY|YEARLY|CUSTOM_DAYS)$")
    recurrence_interval: Optional[str] = None
    recurrence_interval_days: Optional[int] = None
    recurrence_strategy: Optional[str] = Field(default="SCHEDULED_DATE", pattern="^(SCHEDULED_DATE|PAYMENT_DATE)$")
    category_id: Optional[UUID] = None
    category: Optional[str] = None
    template_id: Optional[UUID] = None
    responsible_member_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=2000)
    reminder_days_before: Optional[List[int]] = None

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if ("expected_amount" not in data or data.get("expected_amount") is None) and "amount" in data:
                data["expected_amount"] = data["amount"]
            if ("recurrence_type" not in data or data.get("recurrence_type") is None) and "recurrence_interval" in data:
                data["recurrence_type"] = data["recurrence_interval"]
        return data

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Bill title must be at least 2 characters.")
        return cleaned

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> str:
        return (v or "INR").strip().upper()


class UpdateBillRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=160)
    expected_amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    due_date: Optional[date] = None
    recurrence_type: Optional[str] = Field(None, pattern="^(NONE|MONTHLY|QUARTERLY|HALF_YEARLY|YEARLY|CUSTOM_DAYS)$")
    recurrence_interval_days: Optional[int] = None
    recurrence_strategy: Optional[str] = Field(None, pattern="^(SCHEDULED_DATE|PAYMENT_DATE)$")
    category_id: Optional[UUID] = None
    responsible_member_id: Optional[UUID] = None
    status: Optional[str] = Field(None, pattern="^(UNPAID|PARTIALLY_PAID|PAID|CANCELLED)$")
    notes: Optional[str] = None
    version: Optional[int] = None


class RecordPaymentRequest(BaseModel):
    amount_paid: Decimal = Field(..., gt=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    paid_date: Optional[date] = None
    paid_by: Optional[UUID] = None
    payment_method: Optional[str] = Field(default="UPI", pattern="^(CASH|BANK_TRANSFER|UPI|CARD|ONLINE|OTHER)$")
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    version: Optional[int] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None


class BillSummaryDTO(BaseModel):
    total_unpaid_count: int = 0
    total_unpaid_amount: Decimal = Decimal("0.00")
    due_today_count: int = 0
    due_today_amount: Decimal = Decimal("0.00")
    overdue_count: int = 0
    overdue_amount: Decimal = Decimal("0.00")
    upcoming_count: int = 0
    upcoming_amount: Decimal = Decimal("0.00")
    paid_this_month_count: int = 0
    paid_this_month_amount: Decimal = Decimal("0.00")
    currency: str = "INR"


class PaginatedBillsResponse(BaseModel):
    items: List[BillDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
