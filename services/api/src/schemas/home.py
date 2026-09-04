from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateHomeRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Name of the household workspace")
    country: Optional[str] = Field(None, max_length=8, description="ISO 3166-1 country code, e.g. IN, US, AE, GB")
    state_province: Optional[str] = Field(None, max_length=64, description="State or province name")
    district_city: Optional[str] = Field(None, max_length=64, description="District or city name")
    postal_code: Optional[str] = Field(None, max_length=32, description="Postal or ZIP code")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 3-letter currency code")
    timezone: str = Field(default="UTC", max_length=64, description="IANA timezone string")
    address: Optional[str] = Field(None, max_length=500, description="Optional physical address or neighborhood")
    avatar_url: Optional[str] = Field(None, max_length=512, description="Optional avatar image URL")
    join_policy: Optional[str] = Field(default="REQUEST_TO_JOIN", pattern="^(REQUEST_TO_JOIN|INVITE_ONLY|PUBLIC_JOIN)$")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Home name must be at least 2 characters long.")
        return cleaned


class UpdateHomeRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    country: Optional[str] = Field(None, max_length=8)
    state_province: Optional[str] = Field(None, max_length=64)
    district_city: Optional[str] = Field(None, max_length=64)
    postal_code: Optional[str] = Field(None, max_length=32)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    timezone: Optional[str] = Field(None, max_length=64)
    address: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=512)
    join_policy: Optional[str] = Field(None, pattern="^(REQUEST_TO_JOIN|INVITE_ONLY|PUBLIC_JOIN)$")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if len(cleaned) < 2:
                raise ValueError("Home name must be at least 2 characters long.")
            return cleaned
        return None


class HomeDTO(BaseModel):
    id: UUID
    name: str
    public_home_id: Optional[str] = None
    home_qr_status: Optional[str] = "ACTIVE"
    home_qr_version: Optional[int] = 1
    home_qr_token: Optional[str] = None
    home_qr_url: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    district_city: Optional[str] = None
    postal_code: Optional[str] = None
    currency: Optional[str] = "USD"
    timezone: Optional[str] = "UTC"
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    join_policy: Optional[str] = "REQUEST_TO_JOIN"
    created_by: Optional[UUID] = None
    role: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HomeDetailDTO(HomeDTO):
    member_count: int = 1
    inventory_count: int = 0
    active_chores_count: int = 0


class HomeIdentityDTO(BaseModel):
    home_id: UUID
    name: str
    public_home_id: str
    qr_token: str
    qr_status: str
    qr_version: int
    qr_url: str
    qr_created_at: Optional[datetime] = None
    qr_revoked_at: Optional[datetime] = None


class HomePublicInfoDTO(BaseModel):
    home_id: UUID
    home_name: str
    public_home_id: str
    owner_name: Optional[str] = None
    member_count: int = 1
    qr_status: str = "ACTIVE"
    join_policy: str = "REQUEST_TO_JOIN"
    is_active: bool = True
    accepts_members: bool = True
    is_already_member: bool = False
    user_membership_status: Optional[str] = None
    has_pending_join_request: bool = False


class CreateJoinRequestInput(BaseModel):
    message: Optional[str] = Field(None, max_length=300)


class JoinRequestDTO(BaseModel):
    id: UUID
    home_id: UUID
    home_name: Optional[str] = None
    user_id: UUID
    display_name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str
    message: Optional[str] = None
    created_at: datetime
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None


class ReviewJoinRequestInput(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    role: Optional[str] = Field("MEMBER", pattern="^(HOME_ADMIN|ADMIN|MEMBER|CHILD|GUEST)$")


# Members & Invitations DTOs
class MemberDTO(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    status: str
    joined_at: Optional[datetime] = None
    access_status: Optional[str] = "ACTIVE"
    access_expires_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    is_expiring_soon: Optional[bool] = False
    plan_name: Optional[str] = None
    is_reserved: Optional[bool] = False


class MemberActivityItemDTO(BaseModel):
    id: UUID
    action: str
    description: str
    created_at: datetime


class MemberDetailDTO(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    status: str
    joined_at: Optional[datetime] = None
    access_status: str = "ACTIVE"
    access_expires_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    is_expiring_soon: bool = False
    plan_name: Optional[str] = None
    is_reserved: bool = False
    mobile_verified: bool = False
    recent_activity: List[MemberActivityItemDTO] = []


class HomeAdminSummaryDTO(BaseModel):
    home_id: UUID
    home_name: str
    public_home_id: str
    qr_status: str
    join_policy: str = "REQUEST_TO_JOIN"
    active_members_count: int = 0
    pending_invitations_count: int = 0
    pending_join_requests_count: int = 0
    expiring_access_count: int = 0
    expired_access_count: int = 0


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(HOME_ADMIN|ADMIN|MEMBER|CHILD|GUEST)$")


class CreateInvitationRequest(BaseModel):
    phone_number: Optional[str] = Field(None, description="Mobile number with country code")
    email: Optional[EmailStr] = None
    role: str = Field(default="MEMBER", pattern="^(HOME_ADMIN|ADMIN|MEMBER|CHILD|GUEST)$")
    invitation_mode: str = Field(default="INVITE_ONLY")

    @field_validator("invitation_mode")
    @classmethod
    def validate_invitation_mode(cls, v: str) -> str:
        cleaned = v.strip().upper() if v else "INVITE_ONLY"
        if cleaned in ["STANDARD", "INVITE_ONLY"]:
            return "INVITE_ONLY"
        elif cleaned in ["SUBSCRIPTION", "INVITE_WITH_SUBSCRIPTION"]:
            return "INVITE_WITH_SUBSCRIPTION"
        return "INVITE_ONLY"


class InvitationDTO(BaseModel):
    id: UUID
    home_id: UUID
    home_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    role: str
    invitation_mode: str = "INVITE_ONLY"
    token: str
    invitation_code: Optional[str] = None
    invite_url: str
    status: str
    invited_by: Optional[UUID] = None
    invited_by_name: Optional[str] = None
    expires_at: datetime
    created_at: Optional[datetime] = None

    @property
    def invite_token(self) -> str:
        return self.token

    @property
    def invitation_link(self) -> str:
        return self.invite_url


class InvitationDetailDTO(BaseModel):
    id: UUID
    home_id: UUID
    home_name: str
    role: str
    token: str
    invitation_code: Optional[str] = None
    status: str
    invited_by_name: Optional[str] = None
    invited_by_email: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    expires_at: datetime
    created_at: Optional[datetime] = None
    is_expired: bool = False
    is_already_member: bool = False
    is_identity_matched: Optional[bool] = None
    identity_mismatch_reason: Optional[str] = None


class RedeemInvitationRequest(BaseModel):
    invitation_code: str = Field(..., min_length=3, max_length=64, description="Human-readable invitation code or token")


class AcceptInvitationResponse(BaseModel):
    home_id: UUID
    home_name: str
    role: str
    message: str


class MessageResponse(BaseModel):
    message: str

