import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SendEmailOTPResponse(BaseModel):
    message: str
    email: str
    cooldown_seconds: int = 60
    expires_in_seconds: int = 600
    is_demo_otp: bool = False
    otp_code: Optional[str] = None


class VerifyEmailOTPRequest(BaseModel):
    otp_code: str = Field(..., min_length=4, max_length=10, description="6-digit email verification code")


class VerifyEmailOTPResponse(BaseModel):
    message: str
    verification_ticket: str
    expires_in_seconds: int = 900


class AdminChangePasswordRequest(BaseModel):
    verification_ticket: str = Field(..., min_length=16, description="Cryptographic single-use verification ticket")
    new_password: str = Field(..., min_length=8, max_length=128, description="New secure password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirmation of new password")

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z).")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter (a-z).")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one numeric digit (0-9).")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*...).")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New password and confirm password do not match.")
        return v


class AdminChangePasswordResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    expires_in: int
