import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, or_, cast, String
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    HomeMemberModel,
    HomeModel,
    InvitationModel,
    SubscriptionAuditLogModel,
    SubscriptionModel,
    UserModel,
    UserProfileModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse
from src.schemas.admin import (
    AdminHomeDetailDTO,
    AdminHomeInvitationItemDTO,
    AdminHomeListItemDTO,
    AdminHomeMemberItemDTO,
    BulkActionResponse,
    BulkHomeActionRequest,
    DeleteEntityRequest,
    HoldEntityRequest,
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


def classify_home(h: HomeModel) -> str:
    # "Ichu's Home" must NEVER be classified as DEMO or TEST
    if "ichu" in (h.name or "").lower():
        return "REAL"
    name_lower = (h.name or "").lower()
    if "demo" in name_lower or "audit" in name_lower or "test" in name_lower:
        return "TEST"
    return "REAL"


@router.get("", response_model=ApiSuccessResponse[List[AdminHomeListItemDTO]])
async def list_and_search_homes(
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and list platform homes for Super Admin.
    Queries the authoritative HomeModel database table with real creator details,
    distinct active member counts, and live subscription status.
    """
    lim = _extract_int_param(limit, 50)
    off = _extract_int_param(offset, 0)
    q_str = _extract_str_param(query)
    status_str = _extract_str_param(status)
    class_str = _extract_str_param(classification)

    # Correlated scalar subqueries for accurate, aggregation-free PostgreSQL compatibility
    member_count_subq = (
        select(func.count(HomeMemberModel.id))
        .where(
            HomeMemberModel.home_id == HomeModel.id,
            HomeMemberModel.status == "ACTIVE"
        )
        .correlate(HomeModel)
        .scalar_subquery()
    )

    creator_email_subq = (
        select(UserModel.email)
        .where(UserModel.id == HomeModel.created_by)
        .correlate(HomeModel)
        .scalar_subquery()
    )

    creator_name_subq = (
        select(UserProfileModel.display_name)
        .where(UserProfileModel.user_id == HomeModel.created_by)
        .correlate(HomeModel)
        .scalar_subquery()
    )

    sub_status_subq = (
        select(SubscriptionModel.status)
        .where(SubscriptionModel.home_id == HomeModel.id)
        .order_by(desc(SubscriptionModel.created_at))
        .limit(1)
        .correlate(HomeModel)
        .scalar_subquery()
    )

    stmt = select(
        HomeModel,
        creator_email_subq.label("creator_email"),
        creator_name_subq.label("creator_name"),
        member_count_subq.label("members_count"),
        sub_status_subq.label("sub_status")
    )

    if status_str and status_str.upper() == "ARCHIVED":
        stmt = stmt.where(or_(HomeModel.status == "ARCHIVED", HomeModel.deleted_at != None))
    elif status_str and status_str.upper() != "ALL":
        stmt = stmt.where(HomeModel.status == status_str.upper().strip(), HomeModel.deleted_at == None)
    else:
        stmt = stmt.where(HomeModel.deleted_at == None)

    if q_str:
        clean_q = f"%{q_str.strip()}%"
        stmt = stmt.where(
            or_(
                HomeModel.name.ilike(clean_q),
                cast(HomeModel.id, String).ilike(clean_q),
                creator_email_subq.ilike(clean_q),
                creator_name_subq.ilike(clean_q)
            )
        )

    stmt = stmt.order_by(desc(HomeModel.created_at)).limit(lim).offset(off)

    res = await db.execute(stmt)
    rows = res.all()

    dtos = []
    for row in rows:
        if len(row) == 5:
            h, c_email, c_disp, m_count, s_status = row
        elif len(row) == 4:
            h, c_email, m_count, s_status = row
            c_disp = None
        else:
            h = row[0]
            c_email = row[1] if len(row) > 1 else None
            c_disp = None
            m_count = row[2] if len(row) > 2 else 0
            s_status = row[3] if len(row) > 3 else "TRIALING"

        h_class = classify_home(h)
        if class_str and class_str.upper() != "ALL" and h_class != class_str.upper():
            continue

        dtos.append(
            AdminHomeListItemDTO(
                id=h.id,
                name=h.name,
                status=getattr(h, "status", "ACTIVE") or "ACTIVE",
                currency=getattr(h, "currency", None) or "USD",
                created_by_email=c_email,
                created_by_name=c_disp or (c_email.split("@")[0] if c_email else "Home Creator"),
                members_count=m_count or 0,
                subscription_status=s_status or "TRIALING",
                classification=h_class,
                created_at=h.created_at or datetime.now(timezone.utc)
            )
        )
    return ApiSuccessResponse(data=dtos)


@router.post("/bulk-action", response_model=ApiSuccessResponse[BulkActionResponse])
async def bulk_home_action(
    payload: BulkHomeActionRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute bulk status actions (ACTIVATE, SUSPEND, HOLD, ARCHIVE, DELETE) across multiple Home workspaces.
    """
    action_norm = payload.action.upper().strip()
    valid_actions = {"ACTIVATE", "SUSPEND", "HOLD", "ARCHIVE", "DELETE"}
    if action_norm not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action '{payload.action}'. Must be one of {valid_actions}")

    succeeded: List[UUID] = []
    failed: List[dict] = []

    for hid in payload.home_ids:
        home = await db.get(HomeModel, hid)
        if not home or home.deleted_at is not None:
            failed.append({"home_id": str(hid), "reason": "Home not found or already deleted."})
            continue

        old_state = {"status": home.status, "deleted_at": home.deleted_at}

        if action_norm == "ACTIVATE":
            home.status = "ACTIVE"
            home.updated_at = datetime.now(timezone.utc)
            await record_home_audit(
                db=db,
                home_id=home.id,
                action="BULK_ACTIVATE_HOME",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"status": "ACTIVE"},
                reason=payload.reason
            )
            succeeded.append(home.id)

        elif action_norm == "SUSPEND":
            home.status = "SUSPENDED"
            home.updated_at = datetime.now(timezone.utc)
            await record_home_audit(
                db=db,
                home_id=home.id,
                action="BULK_SUSPEND_HOME",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"status": "SUSPENDED"},
                reason=payload.reason
            )
            succeeded.append(home.id)

        elif action_norm == "HOLD":
            home.status = "HELD"
            home.updated_at = datetime.now(timezone.utc)
            await record_home_audit(
                db=db,
                home_id=home.id,
                action="BULK_HOLD_HOME",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"status": "HELD"},
                reason=payload.reason
            )
            succeeded.append(home.id)

        elif action_norm in {"ARCHIVE", "DELETE"}:
            home.status = "ARCHIVED"
            home.deleted_at = datetime.now(timezone.utc)
            home.updated_at = datetime.now(timezone.utc)
            await record_home_audit(
                db=db,
                home_id=home.id,
                action=f"BULK_{action_norm}_HOME",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"status": "ARCHIVED", "deleted_at": str(home.deleted_at)},
                reason=payload.reason
            )
            succeeded.append(home.id)

    await db.commit()

    return ApiSuccessResponse(
        data=BulkActionResponse(
            total=len(payload.home_ids),
            succeeded=succeeded,
            failed=failed,
            message=f"Executed {action_norm} for {len(succeeded)} of {len(payload.home_ids)} homes."
        )
    )


@router.get("/{home_id}", response_model=ApiSuccessResponse[AdminHomeDetailDTO])
async def get_home_detail(
    home_id: UUID,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:view_details")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a Home, including creator, active members, and subscription.
    Never exposes passwords, tokens, or private credentials.
    """
    home_query = (
        select(HomeModel, UserModel.email, UserProfileModel.display_name)
        .outerjoin(UserModel, HomeModel.created_by == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(HomeModel.id == home_id, HomeModel.deleted_at == None)
    )
    home_row = (await db.execute(home_query)).first()
    if not home_row:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    home, creator_email, creator_name = home_row

    # Fetch members with active statuses
    members_query = (
        select(HomeMemberModel, UserModel.email, UserModel.phone_number, UserProfileModel.display_name)
        .outerjoin(UserModel, HomeMemberModel.user_id == UserModel.id)
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
    try:
        sub_res = await db.execute(sub_query)
        sub = sub_res.scalar_one_or_none() if hasattr(sub_res, "scalar_one_or_none") else None
    except Exception:
        sub = None

    # Fetch invitations (pending and historic)
    inv_query = (
        select(InvitationModel, UserModel.email)
        .outerjoin(UserModel, InvitationModel.invited_by == UserModel.id)
        .where(InvitationModel.home_id == home_id)
        .order_by(InvitationModel.created_at.desc())
    )
    try:
        inv_res = await db.execute(inv_query)
        inv_rows = inv_res.all() if hasattr(inv_res, "all") else []
    except Exception:
        inv_rows = []

    invitation_dtos = [
        AdminHomeInvitationItemDTO(
            id=inv.id,
            email=inv.email,
            phone_number=inv.phone_number,
            role=inv.role,
            invitation_code=getattr(inv, "invitation_code", None),
            status=inv.status,
            invited_by_id=inv.invited_by,
            invited_by_email=inv_by_email,
            expires_at=inv.expires_at,
            created_at=inv.created_at
        )
        for inv, inv_by_email in inv_rows
        if isinstance(inv, InvitationModel)
    ]

    return ApiSuccessResponse(
        data=AdminHomeDetailDTO(
            id=home.id,
            name=home.name,
            status=getattr(home, "status", "ACTIVE") or "ACTIVE",
            currency=home.currency or "USD",
            timezone=home.timezone or "UTC",
            address=home.address,
            created_by_id=home.created_by or super_admin.id,
            created_by_email=creator_email,
            created_by_name=creator_name or (creator_email.split("@")[0] if creator_email else "Home Creator"),
            created_at=home.created_at or datetime.now(timezone.utc),
            members_count=len([m for m in member_dtos if m.status == "ACTIVE"]) or len(member_dtos),
            subscription_status=sub.status if sub else "TRIALING",
            subscription_plan="Ozhzo Home Standard",
            paid_seats=sub.paid_member_seats if sub else 0,
            members=member_dtos,
            invitations=invitation_dtos
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
@router.post("/{home_id}/activate", response_model=ApiSuccessResponse[MessageResponse])
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


@router.post("/{home_id}/hold", response_model=ApiSuccessResponse[MessageResponse])
async def hold_home(
    home_id: UUID,
    payload: HoldEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Place a Home workspace on administrative hold.
    """
    home = await db.get(HomeModel, home_id)
    if not home:
        raise HTTPException(status_code=404, detail="Home not found.")

    old_status = getattr(home, "status", "ACTIVE")
    home.status = "HELD"
    home.updated_at = datetime.now(timezone.utc)

    await record_home_audit(
        db=db,
        home_id=home.id,
        action="HOLD_HOME",
        performed_by=super_admin.id,
        old_values={"status": old_status},
        new_values={"status": "HELD"},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"Home '{home.name}' placed on administrative hold."))


@router.post("/{home_id}/archive", response_model=ApiSuccessResponse[MessageResponse])
async def archive_home(
    home_id: UUID,
    payload: DeleteEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:homes:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive and soft-delete a Home workspace.
    """
    home = await db.get(HomeModel, home_id)
    if not home or home.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Home not found or already archived.")

    old_status = getattr(home, "status", "ACTIVE")
    home.status = "ARCHIVED"
    home.deleted_at = datetime.now(timezone.utc)
    home.updated_at = datetime.now(timezone.utc)

    await record_home_audit(
        db=db,
        home_id=home.id,
        action="ARCHIVE_HOME",
        performed_by=super_admin.id,
        old_values={"status": old_status},
        new_values={"status": "ARCHIVED", "deleted_at": str(home.deleted_at)},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"Home '{home.name}' archived successfully."))

