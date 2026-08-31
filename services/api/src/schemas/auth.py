from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    phone_number: Optional[str] = Field(None, description="Mobile number with or without country code")
    country_code: Optional[str] = Field(None, description="Country calling code, e.g. +91, +1, +44, +971")
    email: Optional[EmailStr] = None
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class SendOTPRequest(BaseModel):
    phone_number: str = Field(..., description="Mobile number with country code")
    country_code: Optional[str] = None
    purpose: str = Field("REGISTRATION", description="REGISTRATION, LOGIN, INVITATION")


class SendOTPResponse(BaseModel):
    message: str
    phone_number: str
    otp_code: Optional[str] = None  # Populated only in development/test/demo mode
    is_demo_otp: bool = False


class VerifyOTPRequest(BaseModel):
    phone_number: str
    country_code: Optional[str] = None
    otp_code: str = Field(..., min_length=4, max_length=8)
    purpose: str = "REGISTRATION"


class VerifyOTPResponse(BaseModel):
    message: str
    phone_number: str
    is_verified: bool


class LoginRequest(BaseModel):
    login_identifier: Optional[str] = Field(None, description="Email address or mobile number")
    phone_number: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    otp_code: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: Optional[UUID] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    mobile_verified: Optional[bool] = False


class ForgotPasswordRequest(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None  # Populated in development/test environments


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str
