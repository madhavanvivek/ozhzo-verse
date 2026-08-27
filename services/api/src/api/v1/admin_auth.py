import json
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.core.config import settings
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import UserModel, AuditLogModel
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import TokenResponse, RefreshTokenRequest


router = APIRouter(prefix="/admin/auth", tags=["Super Admin Authentication"])
admin_alias_router = APIRouter(prefix="/admin", tags=["Super Admin Authentication Alias"])


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


async def enforce_admin_rate_limit(
    redis_client: redis.Redis,
    identifier: str,
    max_requests: int = 10,
    window_seconds: int = 60
):
    try:
        key = f"rate_limit:admin_login:{identifier}"
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window_seconds)
        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many sign-in attempts. Please try again in a few moments."
            )
    except HTTPException:
        raise
    except Exception:
        pass


@router.post("/login", response_model=ApiSuccessResponse[TokenResponse])
@admin_alias_router.post("/login", response_model=ApiSuccessResponse[TokenResponse])
async def admin_login(
    payload: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Dedicated authoritative authentication endpoint exclusively for Platform Super Administrators.
    Rejects normal household users and issues admin-scoped JWT credentials.
    """
    normalized_email = payload.email.strip().lower()
    await enforce_admin_rate_limit(redis_client, normalized_email, max_requests=10, window_seconds=60)

    # 1. Look up user by email
    query = select(UserModel).where(
        func.lower(UserModel.email) == normalized_email,
        UserModel.deleted_at == None
    ).order_by(UserModel.is_super_admin.desc(), UserModel.created_at.asc())
    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator email or password."
        )

    # 2. Strict Super Admin identity verification
    is_super = bool(
        user.is_super_admin is True or
        user.system_role in ["SUPER_ADMIN", "PLATFORM_ADMIN"]
    )
    if not is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required. Household accounts cannot access the Platform Operations Console."
        )

    # 3. Cryptographic password verification
    authenticated = False
    submitted_pwd = (payload.password or "").strip()
    if user.password_hash:
        authenticated = verify_password(submitted_pwd, user.password_hash)

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator email or password."
        )

    # 4. Issue Admin-scoped tokens
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "role": "SUPER_ADMIN",
            "context": "ADMIN",
            "system_role": user.system_role or "SUPER_ADMIN",
            "is_super_admin": True
        }
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        extra_claims={
            "role": "SUPER_ADMIN",
            "context": "ADMIN"
        }
    )

    # 5. Audit log
    audit = AuditLogModel(
        entity_type="SYSTEM",
        entity_id=user.id,
        action="ADMIN_LOGIN_SUCCESS",
        performed_by=user.id,
        details=json.dumps({"email": user.email, "role": user.system_role})
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id
        )
    )


@router.post("/refresh", response_model=ApiSuccessResponse[TokenResponse])
@admin_alias_router.post("/refresh", response_model=ApiSuccessResponse[TokenResponse])
async def admin_refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an admin-scoped session token.
    """
    token_data = decode_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin refresh token."
        )

    user_id_str = token_data.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    query = select(UserModel).where(
        UserModel.id == user_id,
        UserModel.deleted_at == None
    )
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not (user.is_super_admin or user.system_role in ["SUPER_ADMIN", "PLATFORM_ADMIN"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator account inactive or unauthorized.")

    new_access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "role": "SUPER_ADMIN",
            "context": "ADMIN",
            "system_role": user.system_role or "SUPER_ADMIN",
            "is_super_admin": True
        }
    )
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
        extra_claims={
            "role": "SUPER_ADMIN",
            "context": "ADMIN"
        }
    )

    return ApiSuccessResponse(
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id
        )
    )
