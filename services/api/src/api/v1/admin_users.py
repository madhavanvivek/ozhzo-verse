import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_super_admin
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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and list platform users for Super Admin.
    """
    stmt = (
        select(UserModel, UserProfileModel.display_name, func.count(HomeMemberModel.id).label("homes_count"))
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .outerjoin(HomeMemberModel, UserModel.id == HomeMemberModel.user_id)
        .group_by(UserModel.id, UserProfileModel.display_name)
        .order_by(desc(UserModel.created_at))
        .limit(limit)
        .offset(offset)
    )

    if query:
        stmt = stmt.where(UserModel.email.ilike(f"%{query.strip()}%"))
    if is_active is not None:
        stmt = stmt.where(UserModel.is_active == is_active)

    res = await db.execute(stmt)
    rows = res.all()

    dtos = [
        AdminUserListItemDTO(
            id=u.id,
            email=u.email,
            display_name=disp or "User",
            is_active=u.is_active,
            is_verified=u.is_verified,
            is_super_admin=u.is_super_admin,
            system_role=getattr(u, "system_role", "SUPER_ADMIN" if u.is_super_admin else "USER"),
            homes_count=h_count or 0,
            created_at=u.created_at
        )
        for u, disp, h_count in rows
    ]
    return ApiSuccessResponse(data=dtos)


@router.get("/{user_id}", response_model=ApiSuccessResponse[AdminUserDetailDTO])
async def get_user_detail(
    user_id: UUID,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed profile and Home memberships of a platform user.
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

    return ApiSuccessResponse(
        data=AdminUserDetailDTO(
            id=user.id,
            email=user.email,
            display_name=user.profile.display_name if user.profile else "User",
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_super_admin=user.is_super_admin,
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
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspend a platform user account and record audit trail.
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

    return ApiSuccessResponse(data=MessageResponse(message=f"User {user.email} suspended successfully."))


@router.post("/{user_id}/reactivate", response_model=ApiSuccessResponse[MessageResponse])
async def reactivate_user(
    user_id: UUID,
    payload: ReactivateEntityRequest,
    super_admin: UserModel = Depends(require_super_admin),
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

    return ApiSuccessResponse(data=MessageResponse(message=f"User {user.email} reactivated successfully."))
