import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user
from src.core.security import hash_password, verify_password
from src.core.otp import OTPService, normalize_phone_number
from src.api.v1.auth import enforce_auth_rate_limit
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import AuditLogModel, HomeMemberModel, HomeModel, UserModel, UserProfileModel
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.auth import ChangePasswordRequest, MessageResponse, SendOTPResponse
from src.schemas.common import ApiSuccessResponse
from src.schemas.user import (
    HomeMembershipSummary,
    UpdateProfileRequest,
    UserProfileDTO,
    SendPhoneOTPRequest,
    VerifyPhoneOTPRequest
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ApiSuccessResponse[UserProfileDTO])
async def get_my_profile(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.profile
    if not profile:
        profile = UserProfileModel(
            user_id=current_user.id,
            display_name=current_user.email.split("@")[0] if current_user.email else (current_user.phone_number or "User"),
            phone_number=current_user.phone_number,
            country_code=current_user.country_code,
            timezone="UTC",
            preferred_language="en"
        )
        db.add(profile)
        await db.commit()

    query = (
        select(HomeMemberModel, HomeModel)
        .join(HomeModel, HomeMemberModel.home_id == HomeModel.id)
        .where(
            HomeMemberModel.user_id == current_user.id,
            HomeMemberModel.status == "ACTIVE",
            HomeModel.deleted_at == None
        )
    )
    result = await db.execute(query)
    memberships = result.all()

    homes_summary = [
        HomeMembershipSummary(
            home_id=home.id,
            name=home.name,
            role=member.role,
            status=member.status,
            avatar_url=home.avatar_url
        )
        for member, home in memberships
    ]

    return ApiSuccessResponse(
        data=UserProfileDTO(
            id=current_user.id,
            phone_number=current_user.phone_number,
            country_code=current_user.country_code,
            email=current_user.email,
            display_name=profile.display_name if profile else (current_user.email or "User"),
            avatar_url=profile.avatar_url if profile else None,
            timezone=(profile.timezone if profile else None) or "UTC",
            preferred_language=(profile.preferred_language if profile else None) or "en",
            is_active=bool(current_user.is_active) if current_user.is_active is not None else True,
            is_verified=bool(current_user.is_verified) if current_user.is_verified is not None else False,
            mobile_verified=bool(current_user.mobile_verified) if current_user.mobile_verified is not None else False,
            is_super_admin=bool(current_user.is_super_admin) if current_user.is_super_admin is not None else False,
            system_role=getattr(current_user, "system_role", None) or ("SUPER_ADMIN" if current_user.is_super_admin else "USER"),
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            homes=homes_summary
        )
    )


@router.patch("/me", response_model=ApiSuccessResponse[UserProfileDTO])
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.profile
    if not profile:
        profile = UserProfileModel(
            user_id=current_user.id,
            display_name=current_user.email.split("@")[0] if current_user.email else (current_user.phone_number or "User"),
            phone_number=current_user.phone_number,
            country_code=current_user.country_code,
            timezone="UTC",
            preferred_language="en"
        )
        db.add(profile)

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.phone_number is not None:
        profile.phone_number = payload.phone_number
        current_user.phone_number = payload.phone_number
    if payload.country_code is not None:
        profile.country_code = payload.country_code
        current_user.country_code = payload.country_code
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url
    if payload.timezone is not None:
        profile.timezone = payload.timezone
    if payload.preferred_language is not None:
        profile.preferred_language = payload.preferred_language

    profile.updated_at = datetime.now(timezone.utc)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=UserProfileDTO(
            id=current_user.id,
            phone_number=current_user.phone_number,
            country_code=current_user.country_code,
            email=current_user.email,
            display_name=profile.display_name if profile else (current_user.email or "User"),
            avatar_url=profile.avatar_url if profile else None,
            timezone=(profile.timezone if profile else None) or "UTC",
            preferred_language=(profile.preferred_language if profile else None) or "en",
            is_active=bool(current_user.is_active) if current_user.is_active is not None else True,
            is_verified=bool(current_user.is_verified) if current_user.is_verified is not None else False,
            mobile_verified=bool(current_user.mobile_verified) if current_user.mobile_verified is not None else False,
            is_super_admin=bool(current_user.is_super_admin) if current_user.is_super_admin is not None else False,
            system_role=getattr(current_user, "system_role", None) or ("SUPER_ADMIN" if current_user.is_super_admin else "USER"),
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            homes=[]
        )
    )


@router.patch("/me/password", response_model=ApiSuccessResponse[MessageResponse])
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed."
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Password updated successfully.")
    )


@router.post("/me/phone/send-otp", response_model=ApiSuccessResponse[SendOTPResponse])
async def send_phone_verification_otp(
    payload: SendPhoneOTPRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    normalized_phone = normalize_phone_number(payload.phone_number, payload.country_code)

    # Check if another user already has this phone number verified
    query = select(UserModel).where(
        UserModel.phone_number == normalized_phone,
        UserModel.id != current_user.id,
        UserModel.mobile_verified == True
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This mobile number is already verified by another account."
        )

    await enforce_auth_rate_limit(redis_client, normalized_phone, "send_phone_otp", max_requests=5, window_seconds=60)

    otp_service = OTPService()
    norm_phone, dev_code = await otp_service.create_and_send_otp(db, normalized_phone, purpose="PHONE_VERIFICATION")

    return ApiSuccessResponse(
        data=SendOTPResponse(
            message=f"Verification code sent to {norm_phone}.",
            phone_number=norm_phone,
            otp_code=dev_code
        )
    )


@router.post("/me/phone/verify-otp", response_model=ApiSuccessResponse[UserProfileDTO])
async def verify_phone_verification_otp(
    payload: VerifyPhoneOTPRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    normalized_phone = normalize_phone_number(payload.phone_number, payload.country_code)
    await enforce_auth_rate_limit(redis_client, normalized_phone, "verify_phone_otp", max_requests=10, window_seconds=60)

    otp_service = OTPService()
    await otp_service.verify_otp(db, normalized_phone, payload.otp_code, purpose="PHONE_VERIFICATION")

    current_user.phone_number = normalized_phone
    current_user.country_code = payload.country_code
    current_user.mobile_verified = True
    current_user.is_verified = True
    current_user.updated_at = datetime.now(timezone.utc)

    if current_user.profile:
        current_user.profile.phone_number = normalized_phone
        current_user.profile.country_code = payload.country_code
        current_user.profile.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="USER",
        entity_id=current_user.id,
        action="MOBILE_VERIFIED",
        performed_by=current_user.id,
        details=json.dumps({"phone_number": normalized_phone, "method": "OTP"})
    )
    db.add(audit)
    await db.commit()

    return await get_my_profile(current_user=current_user, db=db)
