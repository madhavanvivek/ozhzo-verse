import abc
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.infrastructure.database.models import OTPVerificationModel


def normalize_phone_number(phone_number: str, country_code: Optional[str] = None) -> str:
    """
    Normalizes a phone number into strict E.164 format (+[country_code][number]).
    Handles spaces, dashes, parentheses, dots, leading zeros, and default country codes.
    Canonicalizes:
      - +91 9876543210 -> +919876543210
      - +919876543210  -> +919876543210
      - 09876543210    -> +919876543210 (or with country_code)
      - 91-9876543210  -> +919876543210
      - 9876543210     -> +919876543210 (or with country_code)
      - 00919876543210 -> +919876543210
    """
    if not phone_number or not isinstance(phone_number, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number is required."
        )

    raw = phone_number.strip()
    # Handle international dialing prefix '00'
    if raw.startswith("00"):
        raw = "+" + raw[2:]

    # Remove all formatting characters
    cleaned = re.sub(r"[\s\-\(\)\.\,]", "", raw)

    if cleaned.startswith("+"):
        digits_only = re.sub(r"[^\d]", "", cleaned[1:])
        cleaned = f"+{digits_only}"
    else:
        digits_only = re.sub(r"[^\d]", "", cleaned)
        if country_code:
            cc = "+" + re.sub(r"[^\d]", "", country_code.strip())
            # If user included leading 0 in local number, strip it
            if digits_only.startswith("0") and len(digits_only) > 6:
                digits_only = digits_only.lstrip("0")
            cleaned = f"{cc}{digits_only}"
        else:
            # Strip leading zero if present
            if digits_only.startswith("0") and len(digits_only) == 11:
                digits_only = digits_only[1:]

            # 10-digit number defaults to standard +91
            if len(digits_only) == 10:
                cleaned = f"+91{digits_only}"
            elif len(digits_only) == 12 and digits_only.startswith("91"):
                cleaned = f"+{digits_only}"
            elif len(digits_only) == 11 and digits_only.startswith("1"):
                cleaned = f"+{digits_only}"
            else:
                cleaned = f"+{digits_only}"

    # E.164 validation: + followed by 7 to 15 digits
    if not re.match(r"^\+[1-9]\d{6,14}$", cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid phone number format. Please provide a valid E.164 phone number with country code."
        )
    return cleaned


class OTPProvider(abc.ABC):
    @abc.abstractmethod
    async def send_otp(self, phone_number: str, otp_code: str, purpose: str) -> bool:
        """Dispatches an OTP to the target phone number."""
        pass


class DevelopmentOTPProvider(OTPProvider):
    """
    Development/Test OTP provider.
    Uses deterministic OTP in test/development environments to avoid external SMS costs.
    """
    async def send_otp(self, phone_number: str, otp_code: str, purpose: str) -> bool:
        # In dev/test, logs the code securely
        return True


class ProductionOTPProvider(OTPProvider):
    """
    Production OTP Provider.
    Ready for SMS/WhatsApp gateway integration (e.g. Twilio, AWS SNS, Karix).
    """
    async def send_otp(self, phone_number: str, otp_code: str, purpose: str) -> bool:
        # Production SMS/WhatsApp dispatch integration point
        return True


def get_otp_provider() -> OTPProvider:
    if settings.ENVIRONMENT in ["production", "staging"]:
        return ProductionOTPProvider()
    return DevelopmentOTPProvider()


class OTPService:
    def __init__(self, provider: Optional[OTPProvider] = None):
        self.provider = provider or get_otp_provider()

    @staticmethod
    def _hash_otp(otp_code: str, phone_number: str) -> str:
        return hashlib.sha256(f"{phone_number}:{otp_code}".encode("utf-8")).hexdigest()

    async def create_and_send_otp(
        self,
        db: AsyncSession,
        phone_number: str,
        purpose: str = "REGISTRATION"
    ) -> Tuple[str, Optional[str]]:
        normalized = normalize_phone_number(phone_number)
        
        # Generate 6-digit OTP code
        if settings.DEMO_OTP_ENABLED or settings.ENVIRONMENT in ["development", "test"]:
            otp_code = settings.DEMO_OTP_CODE
        else:
            otp_code = f"{secrets.randbelow(900000) + 100000}"

        otp_hash = self._hash_otp(otp_code, normalized)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Invalidate previous unverified OTPs for this phone and purpose
        query = select(OTPVerificationModel).where(
            OTPVerificationModel.phone_number == normalized,
            OTPVerificationModel.purpose == purpose,
            OTPVerificationModel.is_verified == False
        )
        result = await db.execute(query)
        for existing in result.scalars().all():
            existing.expires_at = datetime.now(timezone.utc)

        new_otp = OTPVerificationModel(
            phone_number=normalized,
            otp_code_hash=otp_hash,
            purpose=purpose,
            is_verified=False,
            attempts=0,
            expires_at=expires_at
        )
        db.add(new_otp)
        await db.commit()

        await self.provider.send_otp(normalized, otp_code, purpose)

        # Return code in test/dev/demo mode for easy testing/automated validation
        dev_code = otp_code if (settings.DEMO_OTP_ENABLED or settings.ENVIRONMENT in ["development", "test"]) else None
        return normalized, dev_code

    async def verify_otp(
        self,
        db: AsyncSession,
        phone_number: str,
        otp_code: str,
        purpose: str = "REGISTRATION"
    ) -> bool:
        normalized = normalize_phone_number(phone_number)
        otp_hash = self._hash_otp(otp_code.strip(), normalized)

        query = (
            select(OTPVerificationModel)
            .where(
                OTPVerificationModel.phone_number == normalized,
                OTPVerificationModel.purpose == purpose,
                OTPVerificationModel.is_verified == False
            )
            .order_by(OTPVerificationModel.created_at.desc())
        )
        result = await db.execute(query)
        record = result.scalars().first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending OTP request found for this mobile number."
            )

        if record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP code has expired. Please request a new code."
            )

        if record.attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invalid OTP attempts. Please request a new code."
            )

        record.attempts += 1

        if record.otp_code_hash != otp_hash:
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP verification code."
            )

        record.is_verified = True
        await db.commit()
        return True
