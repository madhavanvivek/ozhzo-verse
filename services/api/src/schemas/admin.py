from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Super Admin User Management DTOs
# ------------------------------------------------------------------------------

class AdminUserHomeMembershipDTO(BaseModel):
    home_id: UUID
    home_name: str
    role: str
    status: str
    joined_at: Optional[datetime] = None


class AdminUserDetailDTO(BaseModel):
    id: UUID
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    display_name: str
    avatar_url: Optional[str] = None
    timezone: Optional[str] = "UTC"
    preferred_language: Optional[str] = "en"
    is_active: bool
    is_verified: bool
    mobile_verified: bool = False
    is_super_admin: bool
    system_role: Optional[str] = "USER"  # USER, SUPER_ADMIN, PLATFORM_ADMIN, SUPPORT_ADMIN, ANALYST
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    memberships: List[AdminUserHomeMembershipDTO] = []


class AdminUserListItemDTO(BaseModel):
    id: UUID
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    display_name: str
    is_active: bool
    is_verified: bool
    mobile_verified: bool = False
    is_super_admin: bool
    system_role: Optional[str] = "USER"
    homes_count: int
    created_at: Optional[datetime] = None


# ------------------------------------------------------------------------------
# 2. Super Admin Home Management DTOs
# ------------------------------------------------------------------------------

class AdminHomeMemberItemDTO(BaseModel):
    user_id: UUID
    display_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: str
    status: str
    created_at: Optional[datetime] = None


class AdminHomeDetailDTO(BaseModel):
    id: UUID
    name: str
    status: str  # ACTIVE, SUSPENDED
    currency: Optional[str] = "USD"
    timezone: Optional[str] = "UTC"
    address: Optional[str] = None
    created_by_id: UUID
    created_by_email: Optional[str] = None
    created_by_name: str
    created_at: Optional[datetime] = None
    members_count: int
    subscription_status: str
    subscription_plan: str
    paid_seats: int
    members: List[AdminHomeMemberItemDTO] = []


class AdminHomeListItemDTO(BaseModel):
    id: UUID
    name: str
    status: str
    currency: Optional[str] = "USD"
    created_by_email: Optional[str] = None
    created_by_name: Optional[str] = None
    members_count: int
    subscription_status: str
    created_at: Optional[datetime] = None


# ------------------------------------------------------------------------------
# 3. Super Admin Action Payloads
# ------------------------------------------------------------------------------

class SuspendEntityRequest(BaseModel):
    reason: Optional[str] = Field(default="Administrative action", max_length=255)


class ReactivateEntityRequest(BaseModel):
    reason: Optional[str] = Field(default="Administrative reactivation", max_length=255)


class HoldEntityRequest(BaseModel):
    reason: Optional[str] = Field(default="Administrative hold", max_length=255)


class DeleteEntityRequest(BaseModel):
    reason: Optional[str] = Field(default="Administrative deactivation", max_length=255)


class BulkUserActionRequest(BaseModel):
    user_ids: List[UUID]
    action: str  # ACTIVATE, SUSPEND, HOLD, DELETE
    reason: Optional[str] = Field(default="Bulk Administrative Action", max_length=255)


class BulkHomeActionRequest(BaseModel):
    home_ids: List[UUID]
    action: str  # ACTIVATE, SUSPEND, HOLD, ARCHIVE, DELETE
    reason: Optional[str] = Field(default="Bulk Administrative Action", max_length=255)


class BulkActionResponse(BaseModel):
    total: int
    succeeded: List[UUID]
    failed: List[Dict[str, Any]]
    message: str


# ------------------------------------------------------------------------------
# 4. System Configuration & Analytics Foundation DTOs
# ------------------------------------------------------------------------------

class AdminSystemConfigDTO(BaseModel):
    environment: str
    supported_currencies: List[str]
    default_timezone: str
    feature_flags: Dict[str, bool]
    available_system_roles: List[str]
    available_home_roles: List[str]
    password_hashing_algorithm: str
    mfa_enforced_for_admins: bool
    rate_limiting_enabled: bool


class AdminAnalyticsSummaryDTO(BaseModel):
    total_users: int
    active_users: int
    suspended_users: int
    total_homes: int
    active_homes: int
    suspended_homes: int
    average_members_per_home: float
    total_active_subscriptions: int
    total_paid_member_seats: int
    generated_at: datetime


# ------------------------------------------------------------------------------
# 5. Super Admin Activity & Audit DTOs
# ------------------------------------------------------------------------------

class AdminActivityItemDTO(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    performed_by: Optional[UUID] = None
    performed_by_email: Optional[str] = None
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


# ------------------------------------------------------------------------------
# 6. Super Admin Subscribers Listing DTO
# ------------------------------------------------------------------------------

class AdminSubscriberListItemDTO(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_email: Optional[str] = None
    home_id: UUID
    home_name: str
    plan_name: str
    plan_code: str
    status: str
    start_date: Optional[datetime] = None
    renewal_date: Optional[datetime] = None
    coupon_code: Optional[str] = None
    discount_amount: Decimal = Decimal("0.00")
    paid_seats: int = 0
    currency: str = "USD"
    created_at: Optional[datetime] = None

