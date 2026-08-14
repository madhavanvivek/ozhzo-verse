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
    joined_at: datetime


class AdminUserDetailDTO(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    is_verified: bool
    is_super_admin: bool
    system_role: str  # USER, SUPER_ADMIN, PLATFORM_ADMIN, SUPPORT_ADMIN, ANALYST
    created_at: datetime
    updated_at: datetime
    memberships: List[AdminUserHomeMembershipDTO] = []


class AdminUserListItemDTO(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    is_verified: bool
    is_super_admin: bool
    system_role: str
    homes_count: int
    created_at: datetime


# ------------------------------------------------------------------------------
# 2. Super Admin Home Management DTOs
# ------------------------------------------------------------------------------

class AdminHomeMemberItemDTO(BaseModel):
    user_id: UUID
    display_name: str
    email: str
    role: str
    status: str
    created_at: datetime


class AdminHomeDetailDTO(BaseModel):
    id: UUID
    name: str
    status: str  # ACTIVE, SUSPENDED
    currency: str
    timezone: str
    address: Optional[str] = None
    created_by_id: UUID
    created_by_email: str
    created_by_name: str
    created_at: datetime
    members_count: int
    subscription_status: str
    subscription_plan: str
    paid_seats: int
    members: List[AdminHomeMemberItemDTO] = []


class AdminHomeListItemDTO(BaseModel):
    id: UUID
    name: str
    status: str
    currency: str
    created_by_email: str
    members_count: int
    subscription_status: str
    created_at: datetime


# ------------------------------------------------------------------------------
# 3. Super Admin Action Payloads
# ------------------------------------------------------------------------------

class SuspendEntityRequest(BaseModel):
    reason: Optional[str] = Field(default="Administrative action", max_length=255)


class ReactivateEntityRequest(BaseModel):
    reason: Optional[str] = Field(default="Administrative reactivation", max_length=255)


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
