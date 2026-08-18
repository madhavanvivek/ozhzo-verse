import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    HomeMemberModel,
    HomeModel,
    SubscriptionAuditLogModel,
    SubscriptionModel,
    UserModel,
    UserProfileModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse
from src.schemas.admin import (
    AdminHomeDetailDTO,
    AdminHomeListItemDTO,
    AdminHomeMemberItemDTO,
    ReactivateEntityRequest,
    SuspendEntityRequest
)

router = APIRouter(prefix="/admin/homes", tags=["Super Admin - Homes"])


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


async def record_home_audit(
    db: AsyncSession,
    home_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    reason: Optional[str] = None
):
    log = SubscriptionAuditLogModel(
        entity_type="HOME",
        entity_id=home_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason
    )
    db.add(log)


@router.get("", response_model=ApiSuccessResponse[List[AdminHomeListItemDTO]])
async def list_and_search_homes(
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and list platform homes for Super Admin.
    """
    lim = _extract_int_param(limit, 50)
    off = _extract_int_param(offset, 0)
    q_str = _extract_str_param(query)
    status_str = _extract_str_param(status)

    stmt = (
        select(
            HomeModel,
            UserModel.email.label("creator_email"),
            func.count(HomeMemberModel.id).label("members_count"),
            SubscriptionModel.status.label("sub_status")
        )
        .join(UserModel, HomeModel.created_by == UserModel.id)
        .outerjoin(HomeMemberModel, HomeModel.id == HomeMemberModel.home_id)
        .outerjoin(SubscriptionModel, HomeModel.id == SubscriptionModel.home_id)
        .group_by(HomeModel.id, UserModel.email, SubscriptionModel.status)
        .order_by(desc(HomeModel.created_at))
        .limit(lim)
        .offset(off)
    )

    if q_str:
        stmt = stmt.where(HomeModel.name.ilike(f"%{q_str.strip()}%"))
    if status_str:
        stmt = stmt.where(HomeModel.status == status_str.upper().strip())

    res = await db.execute(stmt)
    rows = res.all()

    dtos = [
        AdminHomeListItemDTO(
            id=h.id,
            name=h.name,
            status=getattr(h, "status", "ACTIVE"),
            currency=getattr(h, "currency", None) or "USD",
            created_by_email=c_email,
            members_count=m_count or 0,
            subscription_status=s_status or "TRIALING",
            created_at=h.created_at or datetime.now(timezone.utc)
        )
        for h, c_email, m_count, s_status in rows
    ]
    return ApiSuccessResponse(data=dtos)


@router.get("/{home_id}", response_model=ApiSuccessResponse[AdminHomeDetailDTO])
async def get_home_detail(
    home_id: UUID,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:view_details")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a Home, including creator, active members, and subscription.
    """
    home_query = (
        select(HomeModel, UserModel.email, UserProfileModel.display_name)
        .join(UserModel, HomeModel.created_by == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(HomeModel.id == home_id)
    )
    home_row = (await db.execute(home_query)).first()
    if not home_row:
        raise HTTPException(status_code=404, detail="Home not found.")

    home, creator_email, creator_name = home_row

    # Fetch members
    members_query = (
        select(HomeMemberModel, UserModel.email, UserModel.phone_number, UserProfileModel.display_name)
        .join(UserModel, HomeMemberModel.user_id == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(HomeMemberModel.home_id == home_id)
        .order_by(HomeMemberModel.created_at.asc())
    )
    members_rows = (await db.execute(members_query)).all()

    member_dtos = [
        AdminHomeMemberItemDTO(
            user_id=m.user_id,
            display_name=disp or (u_email.split("@")[0] if u_email else "Member"),
            email=u_email,
            phone_number=u_phone,
            role=m.role,
            status=m.status,
            created_at=m.created_at
        )
        for m, u_email, u_phone, disp in members_rows
    ]

    # Fetch subscription
    sub_query = select(SubscriptionModel).where(SubscriptionModel.home_id == home_id)
    sub = (await db.execute(sub_query)).scalar_one_or_none()

    return ApiSuccessResponse(
        data=AdminHomeDetailDTO(
            id=home.id,
            name=home.name,
            status=getattr(home, "status", "ACTIVE"),
            currency=home.currency,
            timezone=home.timezone,
            address=home.address,
            created_by_id=home.created_by,
            created_by_email=creator_email,
            created_by_name=creator_name or "Home Creator",
            created_at=home.created_at,
            members_count=len(member_dtos),
            subscription_status=sub.status if sub else "TRIALING",
            subscription_plan="Ozhzo Home Standard",
            paid_seats=sub.paid_member_seats if sub else 0,
            members=member_dtos
        )
    )


@router.post("/{home_id}/suspend", response_model=ApiSuccessResponse[MessageResponse])
async def suspend_home(
    home_id: UUID,
    payload: SuspendEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspend a Home workspace and record audit trail.
    """
    home = await db.get(HomeModel, home_id)
    if not home:
        raise HTTPException(status_code=404, detail="Home not found.")

    old_status = getattr(home, "status", "ACTIVE")
    home.status = "SUSPENDED"
    home.updated_at = datetime.now(timezone.utc)

    await record_home_audit(
        db=db,
        home_id=home.id,
        action="SUSPEND_HOME",
        performed_by=super_admin.id,
        old_values={"status": old_status},
        new_values={"status": "SUSPENDED"},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"Home '{home.name}' suspended successfully."))


@router.post("/{home_id}/reactivate", response_model=ApiSuccessResponse[MessageResponse])
async def reactivate_home(
    home_id: UUID,
    payload: ReactivateEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Reactivate a suspended Home workspace and record audit trail.
    """
    home = await db.get(HomeModel, home_id)
    if not home:
        raise HTTPException(status_code=404, detail="Home not found.")

    old_status = getattr(home, "status", "SUSPENDED")
    home.status = "ACTIVE"
    home.updated_at = datetime.now(timezone.utc)

    await record_home_audit(
        db=db,
        home_id=home.id,
        action="REACTIVATE_HOME",
        performed_by=super_admin.id,
        old_values={"status": old_status},
        new_values={"status": "ACTIVE"},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"Home '{home.name}' reactivated successfully."))
