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
    country: Optional[str] = None
    state_province: Optional[str] = None
    district_city: Optional[str] = None
    postal_code: Optional[str] = None
    currency: Optional[str] = "USD"
    timezone: Optional[str] = "UTC"
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    created_by: Optional[UUID] = None
    role: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HomeDetailDTO(HomeDTO):
    member_count: int = 1
    inventory_count: int = 0
    active_chores_count: int = 0


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


class RedeemInvitationRequest(BaseModel):
    invitation_code: str = Field(..., min_length=3, max_length=64, description="Human-readable invitation code or token")


class AcceptInvitationResponse(BaseModel):
    home_id: UUID
    home_name: str
    role: str
    message: str


class MessageResponse(BaseModel):
    message: str

