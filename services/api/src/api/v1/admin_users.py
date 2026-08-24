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
    BulkActionResponse,
    BulkUserActionRequest,
    DeleteEntityRequest,
    HoldEntityRequest,
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


def classify_user(u: UserModel, display_name: Optional[str] = None) -> str:
    # vivek@zinfog.com must NEVER be classified as DEMO or TEST
    if u.email and u.email.lower() == "vivek@zinfog.com":
        return "REAL"
    email_lower = (u.email or "").lower()
    disp_lower = (display_name or "").lower()
    if (
        "example.com" in email_lower
        or "demo_" in email_lower
        or "audit_user" in email_lower
        or "bulk" in email_lower
        or "prodtest" in email_lower
        or "test_" in email_lower
        or "tester" in disp_lower
        or "auditor" in disp_lower
        or "demo" in disp_lower
    ):
        return "TEST"
    return "REAL"


@router.get("", response_model=ApiSuccessResponse[List[AdminUserListItemDTO]])
async def list_and_search_users(
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    system_role: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_admin_permission("admin:users:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and list platform users for Super Admin.
    Supports pagination, search, status/role filtering, and safe sorting without GROUP BY errors.
    """
    lim = _extract_int_param(limit, 50)
    off = _extract_int_param(offset, 0)
    q_str = _extract_str_param(query)
    role_str = _extract_str_param(system_role)
    status_str = _extract_str_param(status)
    class_str = _extract_str_param(classification)
    active_bool = _extract_bool_param(is_active)
    sort_by_str = _extract_str_param(sort_by, "created_at") or "created_at"
    sort_order_str = _extract_str_param(sort_order, "desc") or "desc"

    # Correlated subqueries to avoid PostgreSQL GROUP BY issues
    homes_count_subq = (
        select(func.count(HomeMemberModel.id))
        .where(
            HomeMemberModel.user_id == UserModel.id,
            HomeMemberModel.status == "ACTIVE"
        )
        .correlate(UserModel)
        .scalar_subquery()
    )

    display_name_subq = (
        select(UserProfileModel.display_name)
        .where(UserProfileModel.user_id == UserModel.id)
        .correlate(UserModel)
        .scalar_subquery()
    )

    stmt = select(
        UserModel,
        display_name_subq.label("display_name"),
        homes_count_subq.label("homes_count")
    )

    # Status handling
    if status_str:
        norm_status = status_str.upper().strip()
        if norm_status == "ACTIVE":
            stmt = stmt.where(UserModel.is_active == True, UserModel.deleted_at == None)
        elif norm_status == "SUSPENDED":
            stmt = stmt.where(UserModel.is_active == False, UserModel.deleted_at == None)
        elif norm_status == "DEACTIVATED":
            stmt = stmt.where(UserModel.deleted_at != None)
        elif norm_status != "ALL":
            stmt = stmt.where(UserModel.deleted_at == None)
    elif active_bool is not None:
        stmt = stmt.where(UserModel.is_active == active_bool, UserModel.deleted_at == None)
    else:
        stmt = stmt.where(UserModel.deleted_at == None)

    if q_str:
        clean_q = f"%{q_str.strip()}%"
        stmt = stmt.where(
            or_(
                UserModel.email.ilike(clean_q),
                UserModel.phone_number.ilike(clean_q),
                display_name_subq.ilike(clean_q)
            )
        )

    if role_str:
        norm_role = role_str.upper().strip()
        if norm_role == "SUPER_ADMIN":
            stmt = stmt.where(or_(UserModel.system_role == "SUPER_ADMIN", UserModel.is_super_admin == True))
        elif norm_role == "USER":
            stmt = stmt.where(UserModel.system_role == "USER", UserModel.is_super_admin == False)
        else:
            stmt = stmt.where(UserModel.system_role == norm_role)

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

    dtos = []
    for u, disp, h_count in rows:
        user_class = classify_user(u, disp)
        if class_str and class_str.upper() != "ALL" and user_class != class_str.upper():
            continue
        dtos.append(
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
                classification=user_class,
                homes_count=h_count or 0,
                created_at=u.created_at or datetime.now(timezone.utc)
            )
        )
    return ApiSuccessResponse(data=dtos)


@router.post("/bulk-action", response_model=ApiSuccessResponse[BulkActionResponse])
async def bulk_user_action(
    payload: BulkUserActionRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:users:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute bulk status actions (ACTIVATE, SUSPEND, HOLD, DELETE) across multiple platform users.
    Protects Super Admin self-account from destructive actions.
    """
    action_norm = payload.action.upper().strip()
    valid_actions = {"ACTIVATE", "SUSPEND", "HOLD", "DELETE", "DEACTIVATE", "DELETE_TEST_USERS"}
    if action_norm not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action '{payload.action}'. Must be one of {valid_actions}")

    succeeded: List[UUID] = []
    failed: List[dict] = []

    for uid in payload.user_ids:
        if uid == super_admin.id and action_norm in {"SUSPEND", "HOLD", "DELETE", "DEACTIVATE", "DELETE_TEST_USERS"}:
            failed.append({"user_id": str(uid), "reason": "Super Admin cannot modify or suspend their own account."})
            continue

        user = await db.get(UserModel, uid)
        if not user or (user.deleted_at is not None and action_norm != "ACTIVATE"):
            failed.append({"user_id": str(uid), "reason": "User not found or already deactivated."})
            continue

        # Critical Guardrail: Protected master account vivek@zinfog.com must NEVER be suspended or deleted via bulk action
        if (user.email and user.email.lower() == "vivek@zinfog.com") and action_norm in {"SUSPEND", "HOLD", "DELETE", "DEACTIVATE", "DELETE_TEST_USERS"}:
            failed.append({"user_id": str(uid), "reason": "Protected master Super Admin account cannot be suspended or removed."})
            continue

        old_state = {"is_active": user.is_active, "deleted_at": user.deleted_at}

        if action_norm == "ACTIVATE":
            user.is_active = True
            user.deleted_at = None
            user.updated_at = datetime.now(timezone.utc)
            await record_user_audit(
                db=db,
                user_id=user.id,
                action="BULK_ACTIVATE_USER",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"is_active": True, "deleted_at": None},
                reason=payload.reason
            )
            succeeded.append(user.id)

        elif action_norm == "SUSPEND":
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            await record_user_audit(
                db=db,
                user_id=user.id,
                action="BULK_SUSPEND_USER",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"is_active": False},
                reason=payload.reason
            )
            succeeded.append(user.id)

        elif action_norm == "HOLD":
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            await record_user_audit(
                db=db,
                user_id=user.id,
                action="BULK_HOLD_USER",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"is_active": False, "status_note": "HELD"},
                reason=payload.reason
            )
            succeeded.append(user.id)

        elif action_norm in {"DELETE", "DEACTIVATE", "DELETE_TEST_USERS"}:
            # Check if user owns active homes
            owner_query = select(HomeModel).where(HomeModel.created_by == user.id, HomeModel.deleted_at == None)
            owned_homes = (await db.execute(owner_query)).scalars().all()
            if owned_homes and action_norm != "DELETE_TEST_USERS":
                failed.append({
                    "user_id": str(uid),
                    "reason": f"Cannot delete user who is primary creator of {len(owned_homes)} active home(s). Deactivate or transfer ownership first."
                })
                continue

            user.is_active = False
            user.deleted_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            await record_user_audit(
                db=db,
                user_id=user.id,
                action=f"BULK_{action_norm}_USER",
                performed_by=super_admin.id,
                old_values=old_state,
                new_values={"is_active": False, "deleted_at": str(user.deleted_at)},
                reason=payload.reason
            )
            succeeded.append(user.id)

    await db.commit()

    return ApiSuccessResponse(
        data=BulkActionResponse(
            total=len(payload.user_ids),
            succeeded=succeeded,
            failed=failed,
            message=f"Executed {action_norm} for {len(succeeded)} of {len(payload.user_ids)} users."
        )
    )


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

    if user.email and user.email.lower() == "vivek@zinfog.com":
        raise HTTPException(status_code=400, detail="Protected primary Super Admin account cannot be suspended.")

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
@router.post("/{user_id}/activate", response_model=ApiSuccessResponse[MessageResponse])
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


@router.post("/{user_id}/hold", response_model=ApiSuccessResponse[MessageResponse])
async def hold_user(
    user_id: UUID,
    payload: HoldEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:users:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Place a user account on administrative hold.
    """
    if user_id == super_admin.id:
        raise HTTPException(status_code=400, detail="Super Admin cannot place their own account on hold.")

    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.email and user.email.lower() == "vivek@zinfog.com":
        raise HTTPException(status_code=400, detail="Protected primary Super Admin account cannot be placed on hold.")

    old_state = {"is_active": user.is_active}
    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)

    await record_user_audit(
        db=db,
        user_id=user.id,
        action="HOLD_USER",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values={"is_active": False, "hold_reason": payload.reason},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"User {user.email or user.phone_number or user.id} placed on administrative hold."))


@router.post("/{user_id}/delete", response_model=ApiSuccessResponse[MessageResponse])
async def delete_user(
    user_id: UUID,
    payload: DeleteEntityRequest,
    super_admin: UserModel = Depends(require_admin_permission("admin:users:disable")),
    db: AsyncSession = Depends(get_db),
):
    """
    Safely soft-delete / deactivate a user account with ownership checks.
    """
    if user_id == super_admin.id:
        raise HTTPException(status_code=400, detail="Super Admin cannot delete their own account.")

    user = await db.get(UserModel, user_id)
    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found or already deleted.")

    if user.email and user.email.lower() == "vivek@zinfog.com":
        raise HTTPException(status_code=400, detail="Protected primary Super Admin account cannot be deleted.")

    # Validate active home ownership
    owner_query = select(HomeModel).where(HomeModel.created_by == user.id, HomeModel.deleted_at == None)
    owned_homes = (await db.execute(owner_query)).scalars().all()
    if owned_homes:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete user who is primary creator of {len(owned_homes)} active home(s). Deactivate or transfer ownership first."
        )

    old_state = {"is_active": user.is_active, "deleted_at": user.deleted_at}
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)

    await record_user_audit(
        db=db,
        user_id=user.id,
        action="SAFE_DELETE_USER",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values={"is_active": False, "deleted_at": str(user.deleted_at)},
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"User {user.email or user.phone_number or user.id} deactivated and soft-deleted safely."))
