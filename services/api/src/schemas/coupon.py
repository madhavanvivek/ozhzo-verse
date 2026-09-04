from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Campaign DTOs
# ------------------------------------------------------------------------------

class CampaignDTO(BaseModel):
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    status: str  # ACTIVE, INACTIVE, SCHEDULED, EXPIRED
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget_limit: Optional[Decimal] = None
    maximum_redemptions: Optional[int] = None
    redemptions_count: int = 0
    country: Optional[str] = None
    state: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="ACTIVE")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget_limit: Optional[Decimal] = None
    maximum_redemptions: Optional[int] = None
    country: Optional[str] = None
    state: Optional[str] = None


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    end_date: Optional[datetime] = None
    budget_limit: Optional[Decimal] = None
    maximum_redemptions: Optional[int] = None
    reason: Optional[str] = None


# ------------------------------------------------------------------------------
# 2. Coupon DTOs (First-Class Independent Entity)
# ------------------------------------------------------------------------------

class CouponDTO(BaseModel):
    id: UUID
    campaign_id: Optional[UUID] = None
    name: str
    code: str
    description: Optional[str] = None
    coupon_type: str  # PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, FREE_PERIOD
    discount_value: Decimal
    free_period_value: int
    free_period_unit: str  # DAYS, MONTHS, YEARS
    eligibility_type: str  # ANY_USER, NEW_USER, EXISTING_USER, NEW_HOME, EXISTING_HOME, INVITED_USER, SPECIFIC_USER, SPECIFIC_HOME
    target_user_id: Optional[UUID] = None
    target_home_id: Optional[UUID] = None
    country: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None
    currency: Optional[str] = None
    applicable_plan_id: Optional[UUID] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    maximum_total_redemptions: Optional[int] = None
    redemptions_count: int = 0
    maximum_redemptions_per_user: int = 1
    maximum_redemptions_per_home: int = 1
    allow_stacking: bool = False
    status: str  # ACTIVE, INACTIVE, EXPIRED, SCHEDULED
    notes: Optional[str] = None
    internal_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateCouponRequest(BaseModel):
    campaign_id: Optional[UUID] = None
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    coupon_type: str = Field(default="PERCENTAGE_DISCOUNT")  # PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, FREE_PERIOD
    discount_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    free_period_value: int = Field(default=0, ge=0)
    free_period_unit: str = Field(default="MONTHS")  # DAYS, MONTHS, YEARS
    eligibility_type: str = Field(default="ANY_USER")
    target_user_id: Optional[UUID] = None
    target_home_id: Optional[UUID] = None
    country: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None
    currency: Optional[str] = None
    applicable_plan_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    maximum_total_redemptions: Optional[int] = None
    maximum_redemptions_per_user: int = Field(default=1, ge=1)
    maximum_redemptions_per_home: int = Field(default=1, ge=1)
    allow_stacking: bool = False
    status: str = Field(default="ACTIVE")
    notes: Optional[str] = None
    internal_reason: Optional[str] = None


class UpdateCouponRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    coupon_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    free_period_value: Optional[int] = None
    free_period_unit: Optional[str] = None
    eligibility_type: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    applicable_plan_id: Optional[UUID] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    maximum_total_redemptions: Optional[int] = None
    maximum_redemptions_per_user: Optional[int] = None
    maximum_redemptions_per_home: Optional[int] = None
    notes: Optional[str] = None
    internal_reason: Optional[str] = None


# ------------------------------------------------------------------------------
# 3. Direct Super Admin Grants
# ------------------------------------------------------------------------------

class SubscriptionGrantDTO(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    home_id: UUID
    plan_id: UUID
    grant_type: str  # FREE_PERIOD, PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, EXTENDED_TRIAL
    duration_value: int
    duration_unit: str  # DAYS, MONTHS, YEARS
    discount_value: Decimal
    start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: str  # ACTIVE, EXPIRED, REVOKED
    reason: str
    granted_by: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateSubscriptionGrantRequest(BaseModel):
    home_id: UUID
    user_id: Optional[UUID] = None
    plan_id: Optional[UUID] = None
    grant_type: str = Field(default="FREE_PERIOD")  # FREE_PERIOD, PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, EXTENDED_TRIAL
    duration_value: int = Field(default=6, ge=1)
    duration_unit: str = Field(default="MONTHS")  # DAYS, MONTHS, YEARS
    discount_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    reason: str = Field(..., min_length=3, max_length=255)


# ------------------------------------------------------------------------------
# 4. Coupon Redemptions & Analytics
# ------------------------------------------------------------------------------

class CouponRedemptionDTO(BaseModel):
    id: UUID
    coupon_id: UUID
    coupon_code: str
    campaign_id: Optional[UUID] = None
    user_id: UUID
    home_id: UUID
    discount_amount_applied: Decimal
    free_days_granted: int
    redeemed_at: datetime


class CouponAnalyticsDTO(BaseModel):
    total_coupons: int
    active_coupons: int
    expired_coupons: int
    total_campaigns: int
    total_redemptions: int
    free_users_generated: int
    paid_conversions: int
    coupon_conversion_rate: float
    total_direct_grants: int
    active_direct_grants: int
    generated_at: datetime


# ------------------------------------------------------------------------------
# 5. Coupon Application & Validation Quotes
# ------------------------------------------------------------------------------

class ApplyCouponRequest(BaseModel):
    coupon_code: str = Field(..., min_length=2, max_length=64)
    home_id: UUID
    country: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None


class ApplyCouponResponse(BaseModel):
    coupon_code: str
    coupon_type: str  # PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, FREE_PERIOD
    benefit_description: str
    is_free_period: bool
    free_days_granted: int
    free_period_expiry: Optional[datetime] = None
    list_price: Decimal
    discount_amount: Decimal
    effective_price: Decimal
    payment_required: bool
    redemption_status: str
