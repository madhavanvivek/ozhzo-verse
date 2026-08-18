import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    HomeMemberModel,
    HomeModel,
    SubscriptionAuditLogModel,
    UserModel,
    UserProfileModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse
from src.schemas.admin import (
    AdminUserDetailDTO,
    AdminUserHomeMembershipDTO,
    AdminUserListItemDTO,
    ReactivateEntityRequest,
    SuspendEntityRequest
)

router = APIRouter(prefix="/admin/users", tags=["Super Admin - Users"])


def _extract_int_param(param_val: Any, default_val: int) -> int:
    if hasattr(param_val, "default") and not isinstance(param_val, int):
        return int(param_val.default)
    try:
        return int(param_val)
    except (TypeError, ValueError):
        return default_val


def _extract_str_param(param_val: Any, default_val: Optional[str] = None) -> Optional[str]:
    if param_val is None:
        return default_val
    if isinstance(param_val, str):
        return param_val
    if hasattr(param_val, "default") and isinstance(param_val.default, str):
        return param_val.default
    return default_val


def _extract_bool_param(param_val: Any) -> Optional[bool]:
    if isinstance(param_val, bool):
        return param_val
    if hasattr(param_val, "default") and isinstance(param_val.default, bool):
        return param_val.default
    return None


async def record_user_audit(
    db: AsyncSession,
    user_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    reason: Optional[str] = None
):
    log = SubscriptionAuditLogModel(
        entity_type="USER",
        entity_id=user_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason
    )
    db.add(log)


@router.get("", response_model=ApiSuccessResponse[List[AdminUserListItemDTO]])
async def list_and_search_users(
    query: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    system_role: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_admin_permission("admin:users:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and list platform users for Super Admin.
    Supports pagination, search, status/role filtering, and safe sorting.
    """
    lim = _extract_int_param(limit, 50)
    off = _extract_int_param(offset, 0)
    q_str = _extract_str_param(query)
    role_str = _extract_str_param(system_role)
    active_bool = _extract_bool_param(is_active)
    sort_by_str = _extract_str_param(sort_by, "created_at") or "created_at"
    sort_order_str = _extract_str_param(sort_order, "desc") or "desc"

    stmt = (
        select(UserModel, UserProfileModel.display_name, func.count(HomeMemberModel.id).label("homes_count"))
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .outerjoin(HomeMemberModel, UserModel.id == HomeMemberModel.user_id)
        .group_by(UserModel.id, UserProfileModel.display_name)
    )

    if q_str:
        clean_q = f"%{q_str.strip()}%"
        stmt = stmt.where(
            or_(
                UserModel.email.ilike(clean_q),
                UserModel.phone_number.ilike(clean_q),
                UserProfileModel.display_name.ilike(clean_q)
            )
        )

    if active_bool is not None:
        stmt = stmt.where(UserModel.is_active == active_bool)

    if role_str:
        stmt = stmt.where(UserModel.system_role == role_str.upper().strip())

    # Safe sorting
    sort_col = UserModel.created_at
    if sort_by_str == "email":
        sort_col = UserModel.email
    elif sort_by_str == "updated_at":
        sort_col = UserModel.updated_at

    if sort_order_str.lower() == "asc":
        stmt = stmt.order_by(asc(sort_col))
    else:
        stmt = stmt.order_by(desc(sort_col))

    stmt = stmt.limit(lim).offset(off)

    res = await db.execute(stmt)
    rows = res.all()

    dtos = [
        AdminUserListItemDTO(
            id=u.id,
            email=u.email,
            phone_number=u.phone_number,
            country_code=u.country_code,
            display_name=disp or (u.email.split("@")[0] if u.email else "User"),
            is_active=bool(u.is_active) if u.is_active is not None else True,
            is_verified=bool(u.is_verified) if u.is_verified is not None else False,
            mobile_verified=bool(u.mobile_verified) if u.mobile_verified is not None else False,
            is_super_admin=bool(u.is_super_admin),
            system_role=getattr(u, "system_role", None) or ("SUPER_ADMIN" if u.is_super_admin else "USER"),
            homes_count=h_count or 0,
            created_at=u.created_at or datetime.now(timezone.utc)
        )
        for u, disp, h_count in rows
    ]
    return ApiSuccessResponse(data=dtos)


@router.get("/{user_id}", response_model=ApiSuccessResponse[AdminUserDetailDTO])
async def get_user_detail(
    user_id: UUID,
    super_admin: UserModel = Depends(require_admin_permission("admin:users:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed profile and Home memberships of a platform user.
    Never exposes passwords, tokens, or private secrets.
    """
    user_query = (
        select(UserModel)
        .options(selectinload(UserModel.profile))
        .where(UserModel.id == user_id)
    )
    user = (await db.execute(user_query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    memberships_query = (
        select(HomeMemberModel, HomeModel.name)
        .join(HomeModel, HomeMemberModel.home_id == HomeModel.id)
        .where(HomeMemberModel.user_id == user_id)
    )
    memberships_rows = (await db.execute(memberships_query)).all()

    membership_dtos = [
        AdminUserHomeMembershipDTO(
            home_id=m.home_id,
            home_name=h_name,
            role=m.role,
            status=m.status,
            joined_at=m.created_at
        )
        for m, h_name in memberships_rows
    ]

    profile = user.profile
    return ApiSuccessResponse(
        data=AdminUserDetailDTO(
            id=user.id,
            email=user.email,
            phone_number=user.phone_number,
            country_code=user.country_code,
            display_name=profile.display_name if profile else (user.email.split("@")[0] if user.email else "User"),
            avatar_url=profile.avatar_url if profile else None,
            timezone=(profile.timezone if profile else None) or "UTC",
            preferred_language=(profile.preferred_language if profile else None) or "en",
            is_active=bool(user.is_active) if user.is_active is not None else True,
            is_verified=bool(user.is_verified) if user.is_verified is not None else False,
            mobile_verified=bool(user.mobile_verified) if user.mobile_verified is not None else False,
            is_super_admin=bool(user.is_super_admin),
            system_role=getattr(user, "system_role", "SUPER_ADMIN" if user.is_super_admin else "USER"),
            created_at=user.created_at,
            updated_at=user.updated_at,
            memberships=membership_dtos
        )
    )


@router.post("/{user_id}/suspend", response_model=ApiSuccessResponse[MessageResponse])
async def suspend_user(
    user_id: UUID,
    payload: SuspendEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:users:disable")),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspend a platform user account and record audit trail.
    Super Admins cannot suspend their own accounts.
    """
    if user_id == super_admin.id:
        raise HTTPException(status_code=400, detail="Super Admin cannot suspend their own account.")

    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    old_state = {"is_active": user.is_active}
    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)

    await record_user_audit(
        db=db,
        user_id=user.id,
        action="SUSPEND_USER",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values={"is_active": False},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"User {user.email or user.phone_number or user.id} suspended successfully."))


@router.post("/{user_id}/reactivate", response_model=ApiSuccessResponse[MessageResponse])
async def reactivate_user(
    user_id: UUID,
    payload: ReactivateEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:users:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Reactivate a suspended user account and record audit trail.
    """
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    old_state = {"is_active": user.is_active}
    user.is_active = True
    user.updated_at = datetime.now(timezone.utc)

    await record_user_audit(
        db=db,
        user_id=user.id,
        action="REACTIVATE_USER",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values={"is_active": True},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"User {user.email or user.phone_number or user.id} reactivated successfully."))
