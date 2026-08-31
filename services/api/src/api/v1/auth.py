import json
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.core.config import settings
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    verify_password
)
from src.core.otp import OTPService, normalize_phone_number
from src.api.dependencies import get_current_user, security_scheme
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import UserModel, UserProfileModel, AuditLogModel
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SendOTPRequest,
    SendOTPResponse,
    TokenResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def enforce_auth_rate_limit(
    redis_client: redis.Redis,
    identifier: str,
    action: str,
    max_requests: int = 10,
    window_seconds: int = 60
):
    try:
        if not identifier:
            return
        key = f"rate_limit:{action}:{identifier.lower().strip()}"
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication requests. Please try again later."
            )
    except HTTPException:
        raise
    except Exception:
        pass


@router.post("/send-otp", response_model=ApiSuccessResponse[SendOTPResponse])
async def send_otp(
    payload: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    normalized_phone = normalize_phone_number(payload.phone_number, payload.country_code)
    await enforce_auth_rate_limit(redis_client, normalized_phone, "send_otp", max_requests=5, window_seconds=60)

    otp_service = OTPService()
    norm_phone, dev_code = await otp_service.create_and_send_otp(db, normalized_phone, payload.purpose)

    return ApiSuccessResponse(
        data=SendOTPResponse(
            message=f"Verification code sent to {norm_phone}.",
            phone_number=norm_phone,
            otp_code=dev_code,
            is_demo_otp=bool(settings.DEMO_OTP_ENABLED or settings.ENVIRONMENT in ["development", "test"])
        )
    )


@router.post("/verify-otp", response_model=ApiSuccessResponse[VerifyOTPResponse])
async def verify_otp(
    payload: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    normalized_phone = normalize_phone_number(payload.phone_number, payload.country_code)
    await enforce_auth_rate_limit(redis_client, normalized_phone, "verify_otp", max_requests=10, window_seconds=60)

    otp_service = OTPService()
    await otp_service.verify_otp(db, normalized_phone, payload.otp_code, payload.purpose)

    # If user exists, mark mobile_verified
    query = select(UserModel).where(UserModel.phone_number == normalized_phone)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user:
        user.mobile_verified = True
        user.is_verified = True
        user.updated_at = datetime.now(timezone.utc)
        
        # Log audit
        audit = AuditLogModel(
            entity_type="USER",
            entity_id=user.id,
            action="USER_VERIFIED",
            performed_by=user.id,
            details=json.dumps({"phone_number": normalized_phone, "method": "OTP"})
        )
        db.add(audit)
        await db.commit()

    return ApiSuccessResponse(
        data=VerifyOTPResponse(
            message="Mobile number successfully verified.",
            phone_number=normalized_phone,
            is_verified=True
        )
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[TokenResponse])
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    normalized_phone = None
    if payload.phone_number:
        normalized_phone = normalize_phone_number(payload.phone_number, payload.country_code)
        await enforce_auth_rate_limit(redis_client, normalized_phone, "register", max_requests=10, window_seconds=60)

        # 1. Check duplicate mobile number
        query = select(UserModel).where(UserModel.phone_number == normalized_phone)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this mobile number already exists."
            )

    normalized_email = payload.email.lower() if payload.email else None
    if normalized_email:
        await enforce_auth_rate_limit(redis_client, normalized_email, "register", max_requests=10, window_seconds=60)
        query = select(UserModel).where(UserModel.email == normalized_email)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists."
            )

    if not normalized_phone and not normalized_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either a mobile number or email is required for registration."
        )

    # 2. Create User record with Argon2id hash
    new_user = UserModel(
        id=uuid4(),
        phone_number=normalized_phone,
        country_code=payload.country_code,
        email=normalized_email,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_verified=False,
        mobile_verified=False
    )
    db.add(new_user)
    await db.flush()

    # 3. Create User Profile
    new_profile = UserProfileModel(
        user_id=new_user.id,
        display_name=payload.full_name,
        phone_number=normalized_phone,
        country_code=payload.country_code,
        timezone="UTC",
        preferred_language="en"
    )
    db.add(new_profile)

    # 4. Audit Log
    audit = AuditLogModel(
        entity_type="USER",
        entity_id=new_user.id,
        action="USER_CREATED",
        performed_by=new_user.id,
        details=json.dumps({"phone_number": normalized_phone, "email": normalized_email})
    )
    db.add(audit)
    await db.commit()

    # 5. Issue access and refresh token pair
    access_token = create_access_token(subject=str(new_user.id))
    refresh_token = create_refresh_token(subject=str(new_user.id))

    return ApiSuccessResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=new_user.id,
            phone_number=new_user.phone_number,
            email=new_user.email,
            mobile_verified=bool(new_user.mobile_verified) if new_user.mobile_verified is not None else False
        )
    )


async def enforce_auth_rate_limit(
    redis_client: redis.Redis,
    identifier: str,
    action: str,
    max_requests: int = 10,
    window_seconds: int = 60
):
    try:
        key = f"rate_limit:{action}:{identifier}"
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication requests. Please try again later."
            )
    except HTTPException:
        raise
    except Exception:
        pass


def _extract_authenticated_user(result: Any) -> UserModel | None:
    if result is None:
        return None
    try:
        if hasattr(result, "scalar_one_or_none"):
            u = result.scalar_one_or_none()
            if u is not None and isinstance(u, UserModel):
                return u
    except Exception:
        pass
    try:
        if hasattr(result, "scalars"):
            scalars_obj = result.scalars()
            if hasattr(scalars_obj, "all"):
                users = scalars_obj.all()
                if isinstance(users, list) and users:
                    for u in users:
                        if getattr(u, "is_active", True) and not getattr(u, "deleted_at", None):
                            return u
                    return users[0]
            if hasattr(scalars_obj, "first"):
                first = scalars_obj.first()
                if first is not None and isinstance(first, UserModel):
                    return first
    except Exception:
        pass
    return None


@router.post("/login", response_model=ApiSuccessResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Unified authentication endpoint exclusively for normal Ozhzo household users.
    Accepts either Email or Mobile Number in login_identifier (or phone_number / email).
    Platform Super Admins must authenticate via /admin/auth/login.
    """
    raw_identifier = (
        payload.login_identifier or
        payload.email or
        payload.phone_number or
        ""
    ).strip()

    if not raw_identifier:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide an email address or mobile number to sign in."
        )

    user = None
    is_phone_login = False

    # 1. Resolve Identifier: Email vs Mobile Number
    if "@" in raw_identifier:
        normalized_email = raw_identifier.lower().strip()
        await enforce_auth_rate_limit(redis_client, normalized_email, "login", max_requests=10, window_seconds=60)

        query = select(UserModel).where(
            func.lower(UserModel.email) == normalized_email,
            UserModel.is_active == True,
            UserModel.deleted_at == None
        ).order_by(UserModel.created_at.asc())
        result = await db.execute(query)
        user = _extract_authenticated_user(result)
    else:
        is_phone_login = True
        try:
            normalized_phone = normalize_phone_number(raw_identifier)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email/mobile number or password."
            )

        await enforce_auth_rate_limit(redis_client, normalized_phone, "login", max_requests=10, window_seconds=60)

        query = select(UserModel).where(
            UserModel.phone_number == normalized_phone,
            UserModel.is_active == True,
            UserModel.deleted_at == None
        ).order_by(UserModel.created_at.asc())
        result = await db.execute(query)
        user = _extract_authenticated_user(result)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/mobile number or password."
        )

    # Guard: Direct Super Admins to the Administrator Operations Console
    if user.is_super_admin is True or user.system_role in ["SUPER_ADMIN", "PLATFORM_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator accounts must sign in through the Administrator Console at /admin/login."
        )

    # Guard: Unverified mobile login
    if is_phone_login and not user.mobile_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your mobile number before continuing."
        )

    # 2. Verify password or OTP
    authenticated = False
    if payload.password:
        if user.password_hash:
            authenticated = verify_password(payload.password.strip(), user.password_hash)
    elif payload.otp_code and user.phone_number:
        otp_service = OTPService()
        try:
            await otp_service.verify_otp(db, user.phone_number, payload.otp_code, "LOGIN")
            authenticated = True
        except Exception:
            authenticated = False

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/mobile number or password."
        )

    # 3. Issue standard user token pair
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return ApiSuccessResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            mobile_verified=bool(user.mobile_verified) if user.mobile_verified is not None else False
        )
    )


@router.post("/refresh", response_model=ApiSuccessResponse[TokenResponse])
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    try:
        token_data = decode_token(payload.refresh_token)
        user_id_str = token_data.get("sub")
        token_type = token_data.get("type")
        jti = token_data.get("jti")

        if not user_id_str or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user_id = UUID(user_id_str)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if jti:
        try:
            is_revoked = await redis_client.get(f"revoked_token:{jti}")
            if is_revoked:
                raise HTTPException(status_code=401, detail="Refresh token has been revoked")
        except HTTPException:
            raise
        except Exception:
            pass

    query = select(UserModel).where(UserModel.id == user_id, UserModel.is_active == True, UserModel.deleted_at == None)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User account is inactive or not found")

    if jti:
        try:
            await redis_client.set(f"revoked_token:{jti}", "1", ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
        except Exception:
            pass

    new_access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return ApiSuccessResponse(
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            mobile_verified=bool(user.mobile_verified) if user.mobile_verified is not None else False
        )
    )


@router.post("/logout", response_model=ApiSuccessResponse[MessageResponse])
async def logout(
    credentials=Depends(security_scheme),
    current_user: UserModel = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            jti = payload.get("jti")
            if jti:
                await redis_client.set(f"revoked_token:{jti}", "1", ex=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        except Exception:
            pass

    return ApiSuccessResponse(
        data=MessageResponse(message="Successfully logged out and session revoked.")
    )


@router.post("/forgot-password", response_model=ApiSuccessResponse[ForgotPasswordResponse])
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    lookup_str = payload.phone_number or (payload.email.lower() if payload.email else "")
    await enforce_auth_rate_limit(redis_client, lookup_str, "forgot_password", max_requests=5, window_seconds=60)

    query = select(UserModel).where(
        or_(
            UserModel.phone_number == payload.phone_number,
            UserModel.email == (payload.email.lower() if payload.email else None)
        ),
        UserModel.is_active == True,
        UserModel.deleted_at == None
    ).order_by(UserModel.is_super_admin.desc(), UserModel.created_at.asc())
    result = await db.execute(query)
    user = _extract_authenticated_user(result)

    reset_token = None
    if user:
        reset_token = generate_reset_token()
        try:
            await redis_client.set(f"password_reset:{reset_token}", str(user.id), ex=900)
        except Exception:
            pass

    return ApiSuccessResponse(
        data=ForgotPasswordResponse(
            message="If an account exists, instructions have been dispatched.",
            reset_token=reset_token if settings.ENVIRONMENT in ["development", "test"] else None
        )
    )


@router.post("/reset-password", response_model=ApiSuccessResponse[MessageResponse])
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    user_id_str = None
    try:
        user_id_str = await redis_client.get(f"password_reset:{payload.token}")
    except Exception:
        pass

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or previously used password reset token."
        )

    user_id = UUID(user_id_str)
    query = select(UserModel).where(UserModel.id == user_id, UserModel.is_active == True)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="User account not found.")

    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        await redis_client.delete(f"password_reset:{payload.token}")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=MessageResponse(message="Password has been reset successfully. Please log in with your new credentials.")
    )
