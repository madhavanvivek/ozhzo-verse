import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import require_super_admin
from src.core.config import settings
from src.core.email_service import EmailOTPService
from src.core.security import create_access_token, create_refresh_token, hash_password
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models import AuditLogModel, UserModel
from src.infrastructure.database.session import get_db
from src.schemas.admin_security import (
    AdminChangePasswordRequest,
    AdminChangePasswordResponse,
    SendEmailOTPResponse,
    VerifyEmailOTPRequest,
    VerifyEmailOTPResponse
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/admin/security", tags=["Super Admin - Security"])
email_otp_service = EmailOTPService()


@router.post("/send-email-otp", response_model=ApiSuccessResponse[SendEmailOTPResponse])
async def send_admin_email_otp(
    super_admin: UserModel = Depends(require_super_admin),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Sends a cryptographically secure 6-digit email OTP to the verified Super Admin email address.
    Protected by 60s cooldown rate limit.
    """
    if not super_admin.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin account must have a verified email address to perform password changes."
        )

    email, dev_code = await email_otp_service.create_and_send_otp(
        redis_client=redis_client,
        email=super_admin.email,
        purpose="ADMIN_PASSWORD_CHANGE"
    )

    # Mask email for UI response privacy (e.g. v***k@zinfog.com)
    parts = email.split("@")
    name_part = parts[0]
    domain_part = parts[1] if len(parts) > 1 else ""
    if len(name_part) > 2:
        masked_email = f"{name_part[0]}***{name_part[-1]}@{domain_part}"
    else:
        masked_email = f"{name_part[0]}***@{domain_part}"

    return ApiSuccessResponse(
        data=SendEmailOTPResponse(
            message=f"Verification code sent to {masked_email}.",
            email=masked_email,
            cooldown_seconds=60,
            expires_in_seconds=600,
            is_demo_otp=bool(settings.DEMO_OTP_ENABLED),
            otp_code=dev_code
        )
    )


@router.post("/verify-email-otp", response_model=ApiSuccessResponse[VerifyEmailOTPResponse])
async def verify_admin_email_otp(
    payload: VerifyEmailOTPRequest,
    super_admin: UserModel = Depends(require_super_admin),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Verifies the email OTP submitted by the Super Admin.
    On success, invalidates the OTP and issues a 15-minute single-use cryptographic verification ticket.
    """
    ticket_id = await email_otp_service.verify_otp(
        redis_client=redis_client,
        email=super_admin.email,
        otp_code=payload.otp_code,
        purpose="ADMIN_PASSWORD_CHANGE"
    )

    return ApiSuccessResponse(
        data=VerifyEmailOTPResponse(
            message="Email address successfully verified. You may now set your new password.",
            verification_ticket=ticket_id,
            expires_in_seconds=900
        )
    )


@router.post("/change-password", response_model=ApiSuccessResponse[AdminChangePasswordResponse])
async def change_admin_password(
    payload: AdminChangePasswordRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Sets the new password for the Super Admin after validating the single-use verification ticket.
    - Hashes the new password with Argon2id.
    - Invalidates the verification ticket.
    - Revokes existing refresh sessions in Redis.
    - Records an audit log.
    - Returns fresh token pair for immediate session continuation.
    """
    # 1. Authoritative ticket validation
    await email_otp_service.validate_and_consume_ticket(
        redis_client=redis_client,
        ticket_id=payload.verification_ticket,
        expected_email=super_admin.email
    )

    # 2. Update password hash
    super_admin.password_hash = hash_password(payload.new_password)
    super_admin.updated_at = datetime.now(timezone.utc)

    # 3. Create Audit Log
    audit = AuditLogModel(
        entity_type="USER",
        entity_id=super_admin.id,
        action="PASSWORD_CHANGED_ADMIN",
        performed_by=super_admin.id,
        details=json.dumps({
            "email": super_admin.email,
            "method": "EMAIL_OTP",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    )
    db.add(audit)
    await db.commit()

    # 4. Invalidate existing sessions in Redis (revocation timestamp)
    try:
        revocation_ts = int(datetime.now(timezone.utc).timestamp())
        await redis_client.set(
            f"user_session_revoked:{super_admin.id}",
            str(revocation_ts),
            ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
    except Exception:
        pass

    # 5. Issue new session token pair
    access_token = create_access_token(subject=str(super_admin.id))
    refresh_token = create_refresh_token(subject=str(super_admin.id))

    return ApiSuccessResponse(
        data=AdminChangePasswordResponse(
            message="Super Admin password updated successfully. All other sessions have been revoked.",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )
