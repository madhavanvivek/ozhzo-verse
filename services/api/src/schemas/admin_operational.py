from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Regional Configuration DTOs
# ------------------------------------------------------------------------------

class RegionConfigDTO(BaseModel):
    id: UUID
    country_code: str
    country_name: str
    region: str
    currency: str
    default_plan_code: str
    payment_gateway: str
    tax_percentage: Decimal
    is_active: bool
    is_default: bool
    promotional_eligibility_enabled: bool
    metadata_json: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateRegionConfigRequest(BaseModel):
    country_code: str = Field(..., max_length=8)
    country_name: str = Field(..., max_length=100)
    region: str = Field(default="Global", max_length=64)
    currency: str = Field(..., max_length=8)
    default_plan_code: str = Field(default="HOME_STANDARD", max_length=64)
    payment_gateway: str = Field(default="STRIPE", max_length=64)
    tax_percentage: Decimal = Field(default=Decimal("0.00"))
    is_active: bool = True
    is_default: bool = False
    promotional_eligibility_enabled: bool = True
    metadata_json: Dict[str, Any] = {}


class UpdateRegionConfigRequest(BaseModel):
    country_name: Optional[str] = None
    region: Optional[str] = None
    currency: Optional[str] = None
    default_plan_code: Optional[str] = None
    payment_gateway: Optional[str] = None
    tax_percentage: Optional[Decimal] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    promotional_eligibility_enabled: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------------------
# 2. Feature Flag DTOs
# ------------------------------------------------------------------------------

class FeatureFlagDTO(BaseModel):
    id: UUID
    key: str
    name: str
    description: Optional[str] = None
    is_enabled: bool
    target_countries: List[str] = []
    target_plans: List[str] = []
    rollout_percentage: int = 100
    rules_json: Dict[str, Any] = {}
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateFeatureFlagRequest(BaseModel):
    key: str = Field(..., max_length=100)
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    is_enabled: bool = False
    target_countries: List[str] = []
    target_plans: List[str] = []
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    rules_json: Dict[str, Any] = {}
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class UpdateFeatureFlagRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    target_countries: Optional[List[str]] = None
    target_plans: Optional[List[str]] = None
    rollout_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    rules_json: Optional[Dict[str, Any]] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# ------------------------------------------------------------------------------
# 3. Commercial Rules DTOs
# ------------------------------------------------------------------------------

class SystemCommercialRuleDTO(BaseModel):
    id: UUID
    rule_key: str
    rule_name: str
    rule_value: Dict[str, Any]
    description: Optional[str] = None
    category: str
    is_active: bool
    updated_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateCommercialRuleRequest(BaseModel):
    rule_name: Optional[str] = None
    rule_value: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


# ------------------------------------------------------------------------------
# 4. Global Invitations Management DTOs
# ------------------------------------------------------------------------------

class AdminInvitationItemDTO(BaseModel):
    id: UUID
    home_id: UUID
    home_name: str
    invitation_code: str
    role: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    status: str
    invited_by_id: Optional[UUID] = None
    invited_by_name: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    is_expired: bool

    class Config:
        from_attributes = True


class AdminExtendInvitationRequest(BaseModel):
    days_to_add: int = Field(default=7, ge=1, le=90)
    reason: str = Field(..., min_length=3)


class AdminRevokeInvitationRequest(BaseModel):
    reason: str = Field(..., min_length=3)


# ------------------------------------------------------------------------------
# 5. AI Operational Configuration DTOs
# ------------------------------------------------------------------------------

class AdminAIConfigDTO(BaseModel):
    provider: str
    available_providers: List[str]
    default_model: str
    daily_request_limit_default: int
    daily_token_limit_default: int
    monthly_cost_limit_usd_default: Decimal
    total_ai_records: int
    total_estimated_cost_usd: float
    total_tokens_consumed: int
    active_quotas_count: int


class UpdateAdminAIConfigRequest(BaseModel):
    provider: Optional[str] = None
    default_model: Optional[str] = None
    daily_request_limit_default: Optional[int] = None
    daily_token_limit_default: Optional[int] = None
    monthly_cost_limit_usd_default: Optional[Decimal] = None


# ------------------------------------------------------------------------------
# 6. Country-level Business & Retention Analytics DTOs
# ------------------------------------------------------------------------------

class CountryBusinessMetricDTO(BaseModel):
    country_code: str
    country_name: str
    currency: str
    total_users: int
    total_homes: int
    active_subscriptions: int
    paid_subscriptions: int
    mrr_estimated: float
    conversion_rate: float
    coupons_redeemed_count: int


class RetentionMetricsDTO(BaseModel):
    d1_retention_rate: float
    d7_retention_rate: float
    d30_retention_rate: float
    two_plus_module_adoption_rate: float
    weekly_active_households: int
    total_active_households: int


class AdminBroadcastAlertRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    message: str = Field(..., min_length=5)
    priority: str = Field(default="HIGH")  # CRITICAL, HIGH, NORMAL, LOW
    target_country: Optional[str] = None  # None for all
    target_plan: Optional[str] = None  # None for all
    action_url: Optional[str] = None
