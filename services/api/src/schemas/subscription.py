from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Public & Client Subscription DTOs
# ------------------------------------------------------------------------------

class SubscriptionFeatureDTO(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    is_enabled: bool = True
    entitlement_limit: Optional[str] = None


class PromotionDTO(BaseModel):
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    discount_type: str  # PERCENTAGE, FIXED_AMOUNT
    discount_value: Decimal
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str  # ACTIVE, INACTIVE, EXPIRED, SCHEDULED
    currency: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    new_users_only: bool
    existing_users_allowed: bool
    maximum_redemptions: Optional[int] = None
    redemptions_count: int = 0


class SubscriptionPriceDTO(BaseModel):
    id: UUID
    plan_id: UUID
    country: str
    region: str
    currency: str
    billing_period: str
    list_price: Decimal
    additional_member_list_price: Decimal
    base_price: Decimal
    additional_member_price: Decimal
    version: int
    is_active: bool
    effective_from: datetime
    effective_until: Optional[datetime] = None
    active_promotion: Optional[PromotionDTO] = None


class SubscriptionPlanDetailDTO(BaseModel):
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    plan_type: str
    status: str
    included_members: int
    maximum_members: Optional[int] = None
    max_homes: int = 10
    additional_member_allowed: bool
    introductory_enabled: bool
    introductory_duration_days: int
    introductory_price: Decimal
    prices: List[SubscriptionPriceDTO] = []
    features: List[SubscriptionFeatureDTO] = []


class MemberEntitlementDTO(BaseModel):
    user_id: UUID
    display_name: str
    role: str
    is_admin_or_owner: bool
    is_free_entitled: bool
    requires_paid_seat: bool
    is_seat_covered: bool


class HomeSubscriptionOverviewDTO(BaseModel):
    home_id: UUID
    status: str
    plan_name: str
    plan_code: str
    currency: str
    billing_period: str
    
    # Standard Price & Promotional Snapshot
    list_price: Decimal
    additional_member_list_price: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    effective_price: Decimal
    promotion_code: Optional[str] = None
    renewal_policy: str

    introductory_period_starts_at: datetime
    introductory_period_ends_at: datetime
    is_in_introductory_trial: bool
    days_remaining_in_introductory_period: int

    total_active_members: int
    free_entitled_seats: int
    required_paid_seats: int
    active_paid_seats: int
    is_fully_covered: bool

    annual_total_price: Decimal
    members_entitlements: List[MemberEntitlementDTO] = []
    features: List[SubscriptionFeatureDTO] = []


# ------------------------------------------------------------------------------
# Authoritative Calculation Engine Request & Response
# ------------------------------------------------------------------------------

class CalculateSubscriptionRequest(BaseModel):
    additional_seats: int = Field(..., ge=0, le=100)
    country: Optional[str] = "GLOBAL"
    state: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None
    currency: Optional[str] = "USD"
    billing_period: Optional[str] = "ANNUAL"
    plan_code: Optional[str] = "OZHZO_HOME"
    promotion_code: Optional[str] = None
    coupon_code: Optional[str] = None
    user_id: Optional[UUID] = None
    home_id: Optional[UUID] = None


class CalculateSubscriptionResponse(BaseModel):
    plan_code: str
    country: str
    currency: str
    billing_period: str
    
    # List / Standard Price per seat
    list_price: Decimal
    discount_type: str  # NONE, PERCENTAGE, FIXED_AMOUNT, FREE_PERIOD
    discount_value: Decimal
    discount_amount: Decimal
    effective_price: Decimal
    promotion: Optional[str] = None
    promotion_valid: bool
    coupon_code: Optional[str] = None
    coupon_valid: bool = False
    is_free_period: bool = False
    free_days_granted: int = 0
    free_period_expiry: Optional[datetime] = None
    payment_required: bool = True
    
    # Seat breakdown
    included_members: int
    additional_seats: int
    seats_list_total: Decimal
    seats_discount_total: Decimal
    seats_effective_total: Decimal
    
    introductory_admin_free: bool
    total_payable: Decimal
    pricing_date: datetime


class UpdateSubscriptionSeatsRequest(BaseModel):
    paid_member_seats: int = Field(..., ge=0, le=100)


# ------------------------------------------------------------------------------
# Super Admin Mutation Schemas
# ------------------------------------------------------------------------------

class CreateSubscriptionPlanRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    plan_type: str = Field(default="HOME")
    included_members: int = Field(default=1, ge=1)
    maximum_members: Optional[int] = Field(default=10, ge=1)
    max_homes: int = Field(default=10, ge=1)
    additional_member_allowed: bool = True
    introductory_enabled: bool = True
    introductory_duration_days: int = Field(default=365, ge=0)
    introductory_price: Decimal = Field(default=Decimal("0.00"), ge=0)


class UpdateSubscriptionPlanRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    included_members: Optional[int] = None
    maximum_members: Optional[int] = None
    max_homes: Optional[int] = None
    additional_member_allowed: Optional[bool] = None
    introductory_enabled: Optional[bool] = None
    introductory_duration_days: Optional[int] = None
    introductory_price: Optional[Decimal] = None
    reason: Optional[str] = None


class CreateSubscriptionPriceRequest(BaseModel):
    plan_id: UUID
    country: str = Field(default="GLOBAL", max_length=8)
    region: str = Field(default="GLOBAL", max_length=32)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_period: str = Field(default="ANNUAL")
    list_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    additional_member_list_price: Decimal = Field(default=Decimal("20.00"), ge=0)
    base_price: Optional[Decimal] = None
    additional_member_price: Optional[Decimal] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class UpdateSubscriptionPriceRequest(BaseModel):
    list_price: Optional[Decimal] = None
    additional_member_list_price: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    additional_member_price: Optional[Decimal] = None
    is_active: Optional[bool] = None
    effective_until: Optional[datetime] = None
    reason: Optional[str] = None


class CreatePromotionRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    discount_type: str = Field(default="PERCENTAGE")  # PERCENTAGE, FIXED_AMOUNT
    discount_value: Decimal = Field(default=Decimal("50.00"), ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = Field(default="ACTIVE")
    currency: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    applicable_plan_id: Optional[UUID] = None
    new_users_only: bool = False
    existing_users_allowed: bool = True
    maximum_redemptions: Optional[int] = None
    maximum_redemptions_per_user: int = 1
    minimum_purchase: Decimal = Decimal("0.00")


class UpdatePromotionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    status: Optional[str] = None
    end_date: Optional[datetime] = None
    maximum_redemptions: Optional[int] = None
    reason: Optional[str] = None


class CreateSubscriptionFeatureRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None


class UpdateSubscriptionFeatureRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubscriptionAuditLogDTO(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    performed_by: Optional[UUID] = None
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime


# ------------------------------------------------------------------------------
# Stage 2.2 Payment & User Entitlement DTOs
# ------------------------------------------------------------------------------

class UserEntitlementSummaryDTO(BaseModel):
    free_home_consumed: bool
    free_home_included: int
    active_homes_count: int
    total_allowed_homes: int
    can_create_home: bool
    active_subscription: Optional[Dict[str, Any]] = None


class CheckoutSubscriptionRequest(BaseModel):
    plan_id: UUID
    price_id: Optional[UUID] = None
    coupon_code: Optional[str] = None
    currency: str = "USD"
    billing_period: str = "ANNUAL"
    home_id: Optional[UUID] = None


class CheckoutSubscriptionResponse(BaseModel):
    transaction_id: UUID
    provider: str
    provider_transaction_id: str
    amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    currency: str
    status: str
    client_secret: Optional[str] = None
    payment_required: bool


class ConfirmPaymentRequest(BaseModel):
    transaction_id: UUID
    provider_transaction_id: str
    signature: Optional[str] = None


class ConfirmPaymentResponse(BaseModel):
    success: bool
    status: str
    subscription_id: Optional[UUID] = None
    message: str


class PaymentTransactionDTO(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    home_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None
    plan_name: str
    amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    currency: str
    provider: str
    provider_transaction_id: Optional[str] = None
    status: str
    created_at: datetime


class HomeAccessEntitlementDTO(BaseModel):
    id: UUID
    home_id: UUID
    user_id: Optional[UUID] = None
    user_display_name: Optional[str] = None
    user_email: Optional[str] = None
    subscription_id: Optional[UUID] = None
    reserved_identifier_type: Optional[str] = None
    reserved_identifier_value: Optional[str] = None
    entitlement_type: str
    status: str
    starts_at: datetime
    expires_at: datetime
    is_expired: bool
    notes: Optional[str] = None
    created_at: datetime


class ReserveEntitlementRequest(BaseModel):
    identifier_type: str = Field(default="EMAIL")  # PHONE or EMAIL
    identifier_value: str
    duration_days: int = Field(default=365, ge=1, le=3650)
    notes: Optional[str] = None


class UserHomeAccessEntitlementDTO(BaseModel):
    home_id: UUID
    home_name: str
    role: str
    entitlement_id: Optional[UUID] = None
    entitlement_type: str
    status: str
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_expired: bool
    days_remaining: int


