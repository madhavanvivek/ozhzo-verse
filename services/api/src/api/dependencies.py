from uuid import UUID
from fastapi import Depends, Header, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.core.security import decode_token
from src.core.exceptions import PermissionDeniedException
from src.domain.permissions import has_permission, has_platform_permission
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import HomeMemberModel, UserModel
from src.infrastructure.cache.redis_client import get_redis_client

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> UserModel:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id_str = payload.get("sub")
        token_type = payload.get("type")
        jti = payload.get("jti")
        
        if not user_id_str or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type or payload")
        user_id = UUID(user_id_str)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    # Check if token JTI is blacklisted/revoked in Redis
    if jti:
        try:
            is_revoked = await redis_client.get(f"revoked_token:{jti}")
            if is_revoked:
                raise HTTPException(status_code=401, detail="Token has been revoked")
        except Exception:
            pass  # If Redis is temporarily unreachable, fallback to DB verification

    query = (
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.id == user_id, UserModel.is_active == True, UserModel.deleted_at == None)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User account not found, deactivated, or deleted")

    return user


async def require_super_admin(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Guards system-level administrative endpoints.
    Only users with is_super_admin=True or system_role=SUPER_ADMIN can access.
    """
    is_admin = bool(current_user.is_super_admin) or (getattr(current_user, "system_role", "USER") in ["SUPER_ADMIN", "PLATFORM_ADMIN"])
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required to perform this action."
        )
    return current_user


def require_admin_permission(permission: str):
    """
    Fine-grained platform permission dependency checking explicit platform capabilities.
    """
    async def admin_permission_dependency(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if current_user.is_super_admin:
            return current_user
        system_role = getattr(current_user, "system_role", "USER")
        if not has_platform_permission(system_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super Admin privileges required to perform this action."
            )
        return current_user

    return admin_permission_dependency


class HomeContext:
    def __init__(self, home_id: UUID, user: UserModel, role: str):
        self.home_id = home_id
        self.user = user
        self.role = role


def require_home_permission(required_permission: str):
    async def permission_dependency(
        home_id: UUID = Path(...),
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        redis_client: redis.Redis = Depends(get_redis_client),
    ) -> HomeContext:
        query = select(HomeMemberModel).where(
            HomeMemberModel.home_id == home_id,
            HomeMemberModel.user_id == current_user.id,
            HomeMemberModel.status == "ACTIVE"
        )
        result = await db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(status_code=403, detail="You are not an active member of this home.")

        if not has_permission(membership.role, required_permission):
            raise PermissionDeniedException(required_permission)

        return HomeContext(home_id=home_id, user=current_user, role=membership.role)

    return permission_dependency
