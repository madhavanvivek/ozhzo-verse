import abc
import asyncio
import hashlib
import json
import logging
import secrets
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Optional, Tuple
from fastapi import HTTPException, status
import httpx
import redis.asyncio as redis

from src.core.config import settings

logger = logging.getLogger("ozhzo.email")


class EmailProvider(abc.ABC):
    @abc.abstractmethod
    async def send_email(self, recipient_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Dispatches an email to the recipient."""
        pass


class DevelopmentEmailProvider(EmailProvider):
    """
    Development and Test email provider.
    Used when DEMO_OTP_ENABLED=True in development/test environments.
    Logs dispatch safely without exposing sensitive OTP values or requiring live external SMTP/API services.
    """
    async def send_email(self, recipient_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        logger.info(f"[Dev Email Provider] Dispatch simulated for recipient {recipient_email}: Subject='{subject}'")
        return True


class SMTPEmailProvider(EmailProvider):
    """
    Production-grade SMTP Email Provider.
    Executes actual SMTP socket delivery in a separate thread pool to avoid blocking the asyncio event loop.
    Supports STARTTLS (port 587/25) and SSL (port 465).
    """
    def _send_smtp_sync(self, recipient_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        if not settings.SMTP_HOST:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SMTP provider is not configured. Missing SMTP_HOST environment variable."
            )

        msg = EmailMessage()
        sender_header = f"{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_SENDER_ADDRESS}>"
        msg["From"] = sender_header
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.set_content(body)

        if html_body:
            msg.add_alternative(html_body, subtype="html")

        try:
            if settings.SMTP_USE_SSL:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=10) as server:
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    if settings.SMTP_USE_TLS:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)

            logger.info(f"[SMTP Provider] Successfully delivered email to {recipient_email}: Subject='{subject}'")
            return True
        except Exception as e:
            logger.error(f"[SMTP Provider] Failed to dispatch email to {recipient_email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to deliver verification email via SMTP server ({settings.SMTP_HOST}). Please verify SMTP credentials."
            )

    async def send_email(self, recipient_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        return await asyncio.to_thread(self._send_smtp_sync, recipient_email, subject, body, html_body)


class ResendEmailProvider(EmailProvider):
    """
    Production-grade Resend API Transactional Email Provider.
    Dispatches HTTP requests to https://api.resend.com/emails.
    """
    async def send_email(self, recipient_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        if not settings.RESEND_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Resend email provider is not configured. Missing RESEND_API_KEY environment variable."
            )

        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": f"{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_SENDER_ADDRESS}>",
            "to": [recipient_email],
            "subject": subject,
            "text": body
        }
        if html_body:
            payload["html"] = html_body

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://api.resend.com/emails", headers=headers, json=payload)
                if resp.status_code not in [200, 201]:
                    logger.error(f"[Resend Provider] API responded with HTTP {resp.status_code}: {resp.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to deliver email via Resend API: {resp.text}"
                    )
                logger.info(f"[Resend Provider] Successfully dispatched email to {recipient_email}: Subject='{subject}'")
                return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Resend Provider] Network error connecting to Resend API: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to transactional email provider."
            )


class ProductionEmailProvider(EmailProvider):
    """
    Unified Production Email Dispatcher.
    Routes to Resend (if RESEND_API_KEY is configured) or SMTP (if SMTP_HOST is configured).
    If no provider is configured, returns HTTP 503.
    """
    def __init__(self):
        self.smtp_provider = SMTPEmailProvider()
        self.resend_provider = ResendEmailProvider()

    async def send_email(self, recipient_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        if settings.RESEND_API_KEY:
            return await self.resend_provider.send_email(recipient_email, subject, body, html_body)
        elif settings.SMTP_HOST:
            return await self.smtp_provider.send_email(recipient_email, subject, body, html_body)
        else:
            logger.error("[Production Email Provider] Neither SMTP (SMTP_HOST) nor Resend (RESEND_API_KEY) is configured.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Production email provider is not configured. Please configure SMTP credentials (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD) or RESEND_API_KEY in environment variables."
            )


def get_email_provider() -> EmailProvider:
    # If explicit credentials are provided, always allow real delivery
    if settings.RESEND_API_KEY or settings.SMTP_HOST:
        return ProductionEmailProvider()

    # In production/staging without credentials, use ProductionEmailProvider so it returns HTTP 503
    if settings.ENVIRONMENT in ["production", "staging"]:
        return ProductionEmailProvider()

    # In development/test with DEMO_OTP_ENABLED or no credentials, use DevelopmentEmailProvider
    if settings.DEMO_OTP_ENABLED or settings.ENVIRONMENT in ["development", "test"]:
        return DevelopmentEmailProvider()

    return ProductionEmailProvider()


class EmailOTPService:
    def __init__(self, provider: Optional[EmailProvider] = None):
        self.provider = provider or get_email_provider()

    @staticmethod
    def _hash_otp(email: str, otp_code: str) -> str:
        salt = settings.JWT_SECRET_KEY[:16]
        return hashlib.sha256(f"{salt}:{email.lower().strip()}:{otp_code.strip()}".encode("utf-8")).hexdigest()

    async def create_and_send_otp(
        self,
        redis_client: redis.Redis,
        email: str,
        purpose: str = "ADMIN_PASSWORD_CHANGE"
    ) -> Tuple[str, Optional[str]]:
        normalized_email = email.strip().lower()
        
        # 1. Enforce 60-second cooldown rate limit
        cooldown_key = f"email_otp_cooldown:{purpose}:{normalized_email}"
        try:
            is_in_cooldown = await redis_client.get(cooldown_key)
            if is_in_cooldown:
                ttl = await redis_client.ttl(cooldown_key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {max(1, ttl)} seconds before requesting a new verification code."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Redis cooldown check error: {e}")

        # 2. Generate OTP: 123456 only if DEMO_OTP_ENABLED=True, otherwise cryptographically random CSPRNG code
        if settings.DEMO_OTP_ENABLED:
            otp_code = settings.DEMO_OTP_CODE or "123456"
        else:
            otp_code = f"{secrets.randbelow(900000) + 100000}"

        otp_hash = self._hash_otp(normalized_email, otp_code)
        
        # 3. Store hashed OTP payload in Redis with 10-minute expiry (600 seconds)
        storage_key = f"email_otp:{purpose}:{normalized_email}"
        payload = {
            "hash": otp_hash,
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            await redis_client.set(storage_key, json.dumps(payload), ex=600)
            # Set 60-second cooldown
            await redis_client.set(cooldown_key, "1", ex=60)
        except Exception as e:
            logger.warning(f"Redis write error for email OTP: {e}")

        # 4. Dispatch Email with Plain Text and HTML formatting
        subject = "Ozhzo Verse Super Admin Password Change Verification Code"
        body = (
            f"Hello,\n\n"
            f"Your one-time email verification code for Ozhzo Verse Super Admin password change is: {otp_code}\n\n"
            f"This code will expire in 10 minutes.\n"
            f"If you did not initiate this request, please secure your account immediately.\n\n"
            f"— The Ozhzo Verse Team"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; background-color: #0f172a; color: #f8fafc; border-radius: 12px; border: 1px solid #1e293b;">
            <h2 style="color: #f59e0b; margin-top: 0;">Ozhzo Verse Platform Administration</h2>
            <p style="color: #94a3b8; font-size: 14px;">You requested a password change for your Super Administrator account.</p>
            <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0;">
                <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; display: block; margin-bottom: 6px;">One-Time Verification Code</span>
                <span style="font-size: 32px; font-weight: 700; color: #f8fafc; letter-spacing: 0.25em;">{otp_code}</span>
            </div>
            <p style="color: #94a3b8; font-size: 13px; line-height: 1.5;">This verification code will expire in <strong>10 minutes</strong>. If you did not initiate this password change, please review your security settings immediately.</p>
            <hr style="border: none; border-top: 1px solid #1e293b; margin: 24px 0;" />
            <p style="color: #64748b; font-size: 11px; margin: 0;">This is an automated message from the Ozhzo Verse Platform.</p>
        </div>
        """
        
        # Real or simulated dispatch depending on active provider
        await self.provider.send_email(normalized_email, subject, body, html_body)

        # 5. Return code ONLY when DEMO_OTP_ENABLED is True; in production or when False, return None
        dev_code = otp_code if settings.DEMO_OTP_ENABLED else None
        return normalized_email, dev_code

    async def verify_otp(
        self,
        redis_client: redis.Redis,
        email: str,
        otp_code: str,
        purpose: str = "ADMIN_PASSWORD_CHANGE"
    ) -> str:
        normalized_email = email.strip().lower()
        storage_key = f"email_otp:{purpose}:{normalized_email}"

        raw_data = None
        try:
            raw_data = await redis_client.get(storage_key)
        except Exception as e:
            logger.warning(f"Redis read error: {e}")

        if not raw_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending verification code found or code has expired. Please request a new code."
            )

        data = json.loads(raw_data)
        attempts = data.get("attempts", 0)

        # Check maximum 5 attempts
        if attempts >= 5:
            try:
                await redis_client.delete(storage_key)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invalid verification attempts. This verification code has been locked. Please request a new code."
            )

        expected_hash = self._hash_otp(normalized_email, otp_code.strip())
        stored_hash = data.get("hash")

        if stored_hash != expected_hash:
            data["attempts"] = attempts + 1
            try:
                ttl = await redis_client.ttl(storage_key)
                if ttl > 0:
                    await redis_client.set(storage_key, json.dumps(data), ex=ttl)
            except Exception:
                pass
            remaining = 5 - (attempts + 1)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification code. {remaining} attempt(s) remaining."
            )

        # Verified successfully: Delete OTP and issue a short-lived single-use verification ticket (15 mins = 900s)
        try:
            await redis_client.delete(storage_key)
        except Exception:
            pass

        ticket_id = secrets.token_urlsafe(32)
        ticket_key = f"email_verified_ticket:{ticket_id}"
        try:
            await redis_client.set(ticket_key, normalized_email, ex=900)
        except Exception as e:
            logger.warning(f"Redis ticket save error: {e}")

        return ticket_id

    async def validate_and_consume_ticket(
        self,
        redis_client: redis.Redis,
        ticket_id: str,
        expected_email: str
    ) -> bool:
        ticket_key = f"email_verified_ticket:{ticket_id}"
        ticket_email = None
        try:
            ticket_email = await redis_client.get(ticket_key)
        except Exception as e:
            logger.warning(f"Redis ticket check error: {e}")

        if not ticket_email or ticket_email.strip().lower() != expected_email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or previously used email verification ticket. Please re-verify your email."
            )

        # Invalidate ticket immediately upon use (single-use guarantee)
        try:
            await redis_client.delete(ticket_key)
        except Exception:
            pass

        return True
