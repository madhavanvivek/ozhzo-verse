from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user
from src.core.security import hash_password, verify_password
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import HomeMemberModel, HomeModel, UserModel, UserProfileModel
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.auth import ChangePasswordRequest, MessageResponse
from src.schemas.common import ApiSuccessResponse
from src.schemas.user import HomeMembershipSummary, UpdateProfileRequest, UserProfileDTO

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
