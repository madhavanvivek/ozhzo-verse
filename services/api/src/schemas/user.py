from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class HomeMembershipSummary(BaseModel):
    home_id: UUID
    name: str
    role: str
    status: str = "ACTIVE"
    avatar_url: Optional[str] = None


class UserProfileDTO(BaseModel):
    id: UUID
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    email: Optional[str] = None
    display_name: str
    avatar_url: Optional[str] = None
    timezone: Optional[str] = "UTC"
    preferred_language: Optional[str] = "en"
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False
    mobile_verified: Optional[bool] = False
    is_super_admin: bool = False
    system_role: str = "USER"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    homes: List[HomeMembershipSummary] = []


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=32)
    country_code: Optional[str] = Field(None, max_length=8)
    avatar_url: Optional[str] = Field(None, max_length=512)
    timezone: Optional[str] = Field(None, max_length=64)
    preferred_language: Optional[str] = Field(None, max_length=10)


class SendPhoneOTPRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=32)
    country_code: Optional[str] = Field("+91", max_length=8)


class VerifyPhoneOTPRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=32)
    country_code: Optional[str] = Field("+91", max_length=8)
    otp_code: str = Field(..., min_length=4, max_length=10)
