import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.models import (
    HomeModel,
    InvitationModel,
    SubscriptionAuditLogModel,
    UserModel,
    UserProfileModel,
)
from src.infrastructure.database.session import get_db
from src.schemas.admin_operational import (
    AdminExtendInvitationRequest,
    AdminInvitationItemDTO,
    AdminRevokeInvitationRequest,
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse

router = APIRouter(prefix="/admin/invitations", tags=["Super Admin - Global Invitations"])


async def record_audit_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: dict = None,
    new_values: dict = None,
    reason: str = None,
):
    audit_entry = SubscriptionAuditLogModel(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason,
    )
    db.add(audit_entry)


@router.get("", response_model=ApiSuccessResponse[List[AdminInvitationItemDTO]])
async def list_global_invitations(
    q: Optional[str] = Query(None, description="Search by invitation code, email, or phone"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, ACCEPTED, REVOKED)"),
    home_id: Optional[UUID] = Query(None, description="Filter by specific home ID"),
    limit: int = Query(50, ge=1, le=200),
    super_admin: UserModel = Depends(require_admin_permission("admin:users:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and inspect all household invitations across the platform.
    """
    stmt = (
        select(
            InvitationModel,
            HomeModel.name.label("home_name"),
            UserProfileModel.display_name.label("inviter_name")
        )
        .join(HomeModel, InvitationModel.home_id == HomeModel.id)
        .outerjoin(UserProfileModel, InvitationModel.invited_by == UserProfileModel.user_id)
        .order_by(desc(InvitationModel.created_at))
        .limit(limit)
    )

    if status:
        stmt = stmt.where(InvitationModel.status == status.upper())
    if home_id:
        stmt = stmt.where(InvitationModel.home_id == home_id)
    if q:
        search_pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            (InvitationModel.invitation_code.ilike(search_pattern)) |
            (InvitationModel.email.ilike(search_pattern)) |
            (InvitationModel.phone_number.ilike(search_pattern))
        )

    res = await db.execute(stmt)
    rows = res.all()

    now = datetime.now(timezone.utc)
    results = []
    for inv, home_name, inviter_name in rows:
        results.append(
            AdminInvitationItemDTO(
                id=inv.id,
                home_id=inv.home_id,
                home_name=home_name or "Household",
                invitation_code=inv.invitation_code or "N/A",
                role=inv.role,
                email=inv.email,
                phone_number=inv.phone_number,
                status=inv.status,
                invited_by_id=inv.invited_by,
                invited_by_name=inviter_name or "System",
                expires_at=inv.expires_at,
                created_at=inv.created_at,
                is_expired=bool(inv.expires_at and inv.expires_at < now and inv.status == "PENDING"),
            )
        )

    return ApiSuccessResponse(data=results)


@router.post("/{invitation_id}/extend", response_model=ApiSuccessResponse[MessageResponse])
async def extend_invitation_expiry(
    invitation_id: UUID,
    payload: AdminExtendInvitationRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Operationally extend an expired or stranded invitation's expiration timestamp.
    """
    stmt = select(InvitationModel).where(InvitationModel.id == invitation_id)
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    old_expiry = inv.expires_at
    new_expiry = max(datetime.now(timezone.utc), inv.expires_at) + timedelta(days=payload.days_to_add)
    inv.expires_at = new_expiry
    if inv.status == "EXPIRED":
        inv.status = "PENDING"

    await record_audit_log(
        db,
        entity_type="INVITATION",
        entity_id=inv.id,
        action="ADMIN_EXTEND_INVITATION",
        performed_by=super_admin.id,
        old_values={"expires_at": old_expiry.isoformat() if old_expiry else None, "status": inv.status},
        new_values={"expires_at": new_expiry.isoformat(), "days_added": payload.days_to_add},
        reason=payload.reason,
    )

    await db.commit()
    return ApiSuccessResponse(
        data=MessageResponse(
            message=f"Invitation extended by {payload.days_to_add} days until {new_expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}."
        )
    )


@router.post("/{invitation_id}/revoke", response_model=ApiSuccessResponse[MessageResponse])
async def revoke_invitation_administratively(
    invitation_id: UUID,
    payload: AdminRevokeInvitationRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Administratively revoke an invitation for operational compliance or fraud prevention.
    """
    stmt = select(InvitationModel).where(InvitationModel.id == invitation_id)
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if inv.status == "ACCEPTED":
        raise HTTPException(status_code=400, detail="Cannot revoke an already accepted invitation.")

    old_status = inv.status
    inv.status = "REVOKED"

    await record_audit_log(
        db,
        entity_type="INVITATION",
        entity_id=inv.id,
        action="ADMIN_REVOKE_INVITATION",
        performed_by=super_admin.id,
        old_values={"status": old_status},
        new_values={"status": "REVOKED"},
        reason=payload.reason,
    )

    await db.commit()
    return ApiSuccessResponse(data=MessageResponse(message="Invitation administratively revoked."))
