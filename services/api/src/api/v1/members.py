import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext, security_scheme
from src.core.otp import normalize_phone_number
from src.core.security import decode_token
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AuditLogModel,
    HomeAccessEntitlementModel,
    HomeJoinRequestModel,
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    NotificationModel,
    SubscriptionModel,
    UserModel,
    UserProfileModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.services.notification_service import notification_service
from src.schemas.common import ApiSuccessResponse
from src.schemas.home import (
    AcceptInvitationResponse,
    CreateInvitationRequest,
    HomeAdminSummaryDTO,
    InvitationDTO,
    InvitationDetailDTO,
    MemberActivityItemDTO,
    MemberDTO,
    MemberDetailDTO,
    MessageResponse,
    RedeemInvitationRequest,
    UpdateMemberRoleRequest,
)

router = APIRouter(tags=["Home Members & Invitations"])


def generate_invitation_code() -> str:
    """Generate a high-entropy, human-friendly, uppercase alphanumeric invitation code: OZ-XXXXXX."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"OZ-{random_part}"


def _normalize_utc_dt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


from src.domain.entitlements import (
    check_and_reserve_home_member_seat,
    claim_reserved_entitlement,
    provision_paid_home_entitlement,
    reserve_home_access_entitlement
)


async def check_home_member_seat_limit(home_id: UUID, db: AsyncSession, include_pending: bool = False):
    """Enforce member seat limits based on subscription plan allowance."""
    await check_and_reserve_home_member_seat(home_id, db, include_pending_invitations=include_pending, lock_home=True)


async def _extract_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession,
) -> Optional[UserModel]:
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = UUID(user_id_str)
        query = (
            select(UserModel)
            .options(selectinload(UserModel.profile))
            .where(UserModel.id == user_id, UserModel.is_active == True, UserModel.deleted_at == None)
        )
        res = await db.execute(query)
        return res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 1. Member Management
# ------------------------------------------------------------------------------

@router.get("/homes/{home_id}/members", response_model=ApiSuccessResponse[List[MemberDTO]])
async def list_home_members(
    search: Optional[str] = None,
    status: Optional[str] = "ACTIVE",
    role: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    home_ctx: HomeContext = Depends(require_home_permission("members:view")),
    db: AsyncSession = Depends(get_db)
):
    """
    List members of a Home workspace with server-side search, filtering, and batched access entitlement resolution.
    """
    query = (
        select(HomeMemberModel, UserModel, UserProfileModel)
        .join(UserModel, HomeMemberModel.user_id == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(HomeMemberModel.home_id == home_ctx.home_id)
    )

    if status and status.upper() != "ALL":
        query = query.where(HomeMemberModel.status == status.upper())

    if role:
        query = query.where(HomeMemberModel.role == role.upper())

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(UserProfileModel.display_name).like(s) |
            func.lower(UserModel.email).like(s) |
            UserModel.phone_number.like(s)
        )

    query = query.order_by(HomeMemberModel.joined_at.asc()).offset((max(1, page) - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    # Batched Entitlement resolution
    user_ids = [member.user_id for member, user, profile in rows]
    entitlements_by_user = {}
    if user_ids:
        try:
            ent_q = select(HomeAccessEntitlementModel).where(
                HomeAccessEntitlementModel.home_id == home_ctx.home_id,
                HomeAccessEntitlementModel.user_id.in_(user_ids)
            ).order_by(HomeAccessEntitlementModel.expires_at.desc())
            ent_res = await db.execute(ent_q)
            ents = ent_res.scalars().all() if hasattr(ent_res, "scalars") else []
            for ent in ents:
                if ent.user_id not in entitlements_by_user:
                    entitlements_by_user[ent.user_id] = ent
        except Exception:
            entitlements_by_user = {}

    home = await db.get(HomeModel, home_ctx.home_id)
    now = datetime.now(timezone.utc)

    members_dto = []
    for member, user, profile in rows:
        display_name = profile.display_name if profile else (user.email.split("@")[0] if user.email else user.phone_number or "Member")
        avatar_url = profile.avatar_url if profile else None
        phone_number = user.phone_number or (profile.phone_number if profile else None)

        if member.status in ["REMOVED", "LEFT", "SUSPENDED"]:
            acc_status = member.status
            acc_expires = None
            days_left = None
            expiring_soon = False
            plan_name = None
            is_res = False
        else:
            ent = entitlements_by_user.get(member.user_id)
            if ent and ent.status == "ACTIVE":
                acc_expires = _normalize_utc_dt(ent.expires_at)
                days_left = max(0, (acc_expires - now).days) if acc_expires else None
                if acc_expires and acc_expires < now:
                    acc_status = "EXPIRED"
                    expiring_soon = False
                elif days_left is not None and days_left <= 7:
                    acc_status = "EXPIRING"
                    expiring_soon = True
                else:
                    acc_status = "ACTIVE"
                    expiring_soon = False
                plan_name = getattr(ent, "notes", None) or "Active Entitlement"
                is_res = False
            elif ent and ent.status == "RESERVED":
                acc_status = "PENDING"
                acc_expires = _normalize_utc_dt(ent.expires_at)
                days_left = max(0, (acc_expires - now).days) if acc_expires else None
                expiring_soon = False
                plan_name = "Reserved Seat"
                is_res = True
            else:
                # Check first-year free or home subscription
                if home and home.created_by == member.user_id:
                    home_created_at = _normalize_utc_dt(getattr(home, "created_at", None)) or now
                    first_year_expiry = home_created_at + timedelta(days=365)
                    acc_expires = first_year_expiry
                    days_left = max(0, (first_year_expiry - now).days)
                    if first_year_expiry >= now:
                        acc_status = "EXPIRING" if days_left <= 7 else "ACTIVE"
                        expiring_soon = days_left <= 7
                        plan_name = "First-Year Free Home"
                    else:
                        acc_status = "EXPIRED"
                        expiring_soon = False
                        plan_name = "First-Year Free Home (Expired)"
                elif home and hasattr(home, "subscription") and home.subscription and home.subscription.status in ["ACTIVE", "TRIALING"]:
                    sub = home.subscription
                    sub_exp = _normalize_utc_dt(sub.current_period_ends_at)
                    acc_expires = sub_exp
                    days_left = max(0, (sub_exp - now).days) if sub_exp else None
                    acc_status = "EXPIRING" if (days_left is not None and days_left <= 7) else "ACTIVE"
                    expiring_soon = (days_left is not None and days_left <= 7)
                    plan_name = "Household Subscription"
                else:
                    acc_status = "EXPIRED"
                    acc_expires = None
                    days_left = 0
                    expiring_soon = False
                    plan_name = None
                is_res = False

        members_dto.append(
            MemberDTO(
                id=member.id,
                user_id=user.id,
                display_name=display_name,
                phone_number=phone_number,
                email=user.email,
                avatar_url=avatar_url,
                role=member.role,
                status=member.status,
                joined_at=member.joined_at,
                access_status=acc_status,
                access_expires_at=acc_expires,
                days_until_expiry=days_left,
                is_expiring_soon=expiring_soon,
                plan_name=plan_name,
                is_reserved=is_res
            )
        )

    return ApiSuccessResponse(data=members_dto)


@router.get("/homes/{home_id}/members/{member_id}", response_model=ApiSuccessResponse[MemberDetailDTO])
async def get_home_member_detail(
    member_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("members:view")),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed member information, entitlement status, and recent activity timeline.
    """
    query = (
        select(HomeMemberModel, UserModel, UserProfileModel)
        .join(UserModel, HomeMemberModel.user_id == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(
            HomeMemberModel.id == member_id,
            HomeMemberModel.home_id == home_ctx.home_id
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Home member not found.")

    member, user, profile = row
    display_name = profile.display_name if profile else (user.email.split("@")[0] if user.email else user.phone_number or "Member")
    avatar_url = profile.avatar_url if profile else None
    phone_number = user.phone_number or (profile.phone_number if profile else None)

    # Entitlement status
    ent_q = select(HomeAccessEntitlementModel).where(
        HomeAccessEntitlementModel.home_id == home_ctx.home_id,
        HomeAccessEntitlementModel.user_id == member.user_id
    ).order_by(HomeAccessEntitlementModel.expires_at.desc())
    ent_res = await db.execute(ent_q)
    ent = ent_res.scalars().first() if hasattr(ent_res, "scalars") else None

    now = datetime.now(timezone.utc)
    if member.status in ["REMOVED", "LEFT", "SUSPENDED"]:
        acc_status = member.status
        acc_expires = None
        days_left = None
        expiring_soon = False
        plan_name = None
        is_res = False
    elif ent and ent.status == "ACTIVE":
        acc_expires = _normalize_utc_dt(ent.expires_at)
        days_left = max(0, (acc_expires - now).days) if acc_expires else None
        acc_status = "EXPIRED" if (acc_expires and acc_expires < now) else ("EXPIRING" if days_left is not None and days_left <= 7 else "ACTIVE")
        expiring_soon = (days_left is not None and days_left <= 7)
        plan_name = getattr(ent, "notes", None) or "Active Entitlement"
        is_res = False
    elif ent and ent.status == "RESERVED":
        acc_status = "PENDING"
        acc_expires = _normalize_utc_dt(ent.expires_at)
        days_left = max(0, (acc_expires - now).days) if acc_expires else None
        expiring_soon = False
        plan_name = "Reserved Seat"
        is_res = True
    else:
        acc_status = "ACTIVE" if member.status == "ACTIVE" else member.status
        acc_expires = None
        days_left = None
        expiring_soon = False
        plan_name = "Standard Member"
        is_res = False

    # Recent activity logs for this member
    audit_q = select(AuditLogModel).where(
        (AuditLogModel.entity_type == "HOME_MEMBER") & (AuditLogModel.entity_id == member.id) |
        (AuditLogModel.performed_by == member.user_id)
    ).order_by(AuditLogModel.created_at.desc()).limit(10)
    audit_res = await db.execute(audit_q)
    audits = audit_res.scalars().all() if hasattr(audit_res, "scalars") else []

    activity_items = []
    for a in audits:
        activity_items.append(
            MemberActivityItemDTO(
                id=a.id,
                action=a.action,
                description=f"Action '{a.action}' performed on {a.entity_type}",
                created_at=a.created_at
            )
        )

    return ApiSuccessResponse(
        data=MemberDetailDTO(
            id=member.id,
            user_id=user.id,
            display_name=display_name,
            email=user.email,
            phone_number=phone_number,
            avatar_url=avatar_url,
            role=member.role,
            status=member.status,
            joined_at=member.joined_at,
            access_status=acc_status,
            access_expires_at=acc_expires,
            days_until_expiry=days_left,
            is_expiring_soon=expiring_soon,
            plan_name=plan_name,
            is_reserved=is_res,
            mobile_verified=getattr(user, "mobile_verified", False) or False,
            recent_activity=activity_items
        )
    )


@router.patch("/homes/{home_id}/members/{member_id}/role", response_model=ApiSuccessResponse[MessageResponse])
async def update_member_role(
    member_id: UUID,
    payload: UpdateMemberRoleRequest,
    home_ctx: HomeContext = Depends(require_home_permission("members:manage_roles")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(HomeMemberModel).where(
        HomeMemberModel.id == member_id,
        HomeMemberModel.home_id == home_ctx.home_id,
        HomeMemberModel.status == "ACTIVE"
    )
    result = await db.execute(query)
    target_member = result.scalar_one_or_none()

    if not target_member:
        raise HTTPException(status_code=404, detail="Home member not found.")

    # 1. Owner Protection
    if target_member.role == "OWNER":
        raise HTTPException(status_code=400, detail="Cannot modify the role of the workspace Owner.")

    if target_member.role in ["OWNER", "HOME_ADMIN"] and target_member.user_id != home_ctx.user.id:
        if home_ctx.role not in ["OWNER", "HOME_ADMIN"]:
            raise HTTPException(status_code=403, detail="Only a Home Admin can modify another Admin's role.")

    # 2. Last Admin Protection
    if target_member.role in ["OWNER", "HOME_ADMIN", "ADMIN"] and payload.role not in ["OWNER", "HOME_ADMIN", "ADMIN"]:
        other_admin_q = select(func.count(HomeMemberModel.id)).where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.status == "ACTIVE",
            HomeMemberModel.id != target_member.id,
            HomeMemberModel.role.in_(["OWNER", "HOME_ADMIN", "ADMIN"])
        )
        other_admin_res = await db.execute(other_admin_q)
        other_admin_count = other_admin_res.scalar() if hasattr(other_admin_res, "scalar") else 0
        if not other_admin_count or other_admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining administrator of this Home. Assign another administrator first."
            )

    old_role = target_member.role
    target_member.role = payload.role
    target_member.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME_MEMBER",
        entity_id=target_member.id,
        action="MEMBER_ROLE_CHANGED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"old_role": old_role, "new_role": payload.role})
    )
    db.add(audit)
    await db.commit()

    try:
        await redis_client.delete(f"user:{target_member.user_id}:home:{home_ctx.home_id}:perms")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Member role updated to {payload.role}.")
    )


@router.delete("/homes/{home_id}/members/{member_id}", response_model=ApiSuccessResponse[MessageResponse])
async def remove_home_member(
    member_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("members:remove")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(HomeMemberModel).where(
        HomeMemberModel.id == member_id,
        HomeMemberModel.home_id == home_ctx.home_id,
        HomeMemberModel.status == "ACTIVE"
    )
    result = await db.execute(query)
    target_member = result.scalar_one_or_none()

    if not target_member:
        raise HTTPException(status_code=404, detail="Home member not found.")

    # 1. Owner Protection
    if target_member.role == "OWNER":
        raise HTTPException(status_code=400, detail="Cannot remove the Home workspace Owner.")

    if target_member.role in ["OWNER", "HOME_ADMIN"] and target_member.user_id != home_ctx.user.id:
        if home_ctx.role not in ["OWNER", "HOME_ADMIN"]:
            raise HTTPException(status_code=403, detail="Only a Home Admin can remove another Admin.")

    # 2. Last Admin Protection
    if target_member.role in ["OWNER", "HOME_ADMIN", "ADMIN"]:
        other_admin_q = select(func.count(HomeMemberModel.id)).where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.status == "ACTIVE",
            HomeMemberModel.id != target_member.id,
            HomeMemberModel.role.in_(["OWNER", "HOME_ADMIN", "ADMIN"])
        )
        other_admin_res = await db.execute(other_admin_q)
        other_admin_count = other_admin_res.scalar() if hasattr(other_admin_res, "scalar") else 0
        if not other_admin_count or other_admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last remaining administrator of this Home."
            )

    target_member.status = "REMOVED"
    target_member.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME_MEMBER",
        entity_id=target_member.id,
        action="MEMBER_REMOVED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"user_id": str(target_member.user_id), "role": target_member.role})
    )
    db.add(audit)
    await db.commit()

    try:
        await redis_client.delete(f"user:{target_member.user_id}:homes")
        await redis_client.delete(f"user:{target_member.user_id}:home:{home_ctx.home_id}:perms")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=MessageResponse(message="Member has been removed from this Home.")
    )


@router.post("/homes/{home_id}/members/{member_id}/remind", response_model=ApiSuccessResponse[MessageResponse])
async def remind_member_access_expiry(
    member_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("members:view")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Sends a controlled, deduplicated renewal reminder notification to a member.
    """
    query = select(HomeMemberModel).where(
        HomeMemberModel.id == member_id,
        HomeMemberModel.home_id == home_ctx.home_id,
        HomeMemberModel.status == "ACTIVE"
    )
    member = (await db.execute(query)).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Active home member not found.")

    home = await db.get(HomeModel, home_ctx.home_id)
    home_name = home.name if home else "the Home"

    # Deduplicate reminder
    dedup_key = f"remind:{member.user_id}:{home_ctx.home_id}"
    try:
        if redis_client:
            already_reminded = await redis_client.get(dedup_key)
            if already_reminded:
                return ApiSuccessResponse(
                    data=MessageResponse(message="A reminder has already been sent to this member recently.")
                )
            await redis_client.setex(dedup_key, 86400, "1")
    except Exception:
        pass

    # Create notification
    notif = NotificationModel(
        id=uuid4(),
        home_id=home_ctx.home_id,
        user_id=member.user_id,
        title=f"Access Renewal Reminder for {home_name}",
        body=f"Your subscription access for {home_name} expires soon. Please renew your subscription to maintain continuous access.",
        type="ACCESS_EXPIRY_REMINDER",
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(notif)

    audit = AuditLogModel(
        entity_type="HOME_MEMBER",
        entity_id=member.id,
        action="MEMBER_REMINDED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"target_user_id": str(member.user_id), "home_id": str(home_ctx.home_id)})
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Access renewal reminder sent successfully.")
    )


@router.get("/homes/{home_id}/admin/summary", response_model=ApiSuccessResponse[HomeAdminSummaryDTO])
async def get_home_admin_summary(
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db)
):
    """
    High-performance consolidated summary counts for Home Admin overview.
    """
    home = await db.get(HomeModel, home_ctx.home_id)
    if not home:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    # 1. Active members count
    mem_q = select(func.count(HomeMemberModel.id)).where(
        HomeMemberModel.home_id == home_ctx.home_id,
        HomeMemberModel.status == "ACTIVE"
    )
    mem_count = (await db.execute(mem_q)).scalar() or 0

    # 2. Pending invitations count
    inv_q = select(func.count(InvitationModel.id)).where(
        InvitationModel.home_id == home_ctx.home_id,
        InvitationModel.status == "PENDING"
    )
    inv_count = (await db.execute(inv_q)).scalar() or 0

    # 3. Pending join requests count
    req_q = select(func.count(HomeJoinRequestModel.id)).where(
        HomeJoinRequestModel.home_id == home_ctx.home_id,
        HomeJoinRequestModel.status == "PENDING"
    )
    req_count = (await db.execute(req_q)).scalar() or 0

    # 4. Expiring & expired entitlements
    now = datetime.now(timezone.utc)
    week_ahead = now + timedelta(days=7)

    expiring_q = select(func.count(HomeAccessEntitlementModel.id)).where(
        HomeAccessEntitlementModel.home_id == home_ctx.home_id,
        HomeAccessEntitlementModel.status == "ACTIVE",
        HomeAccessEntitlementModel.expires_at >= now,
        HomeAccessEntitlementModel.expires_at <= week_ahead
    )
    expiring_count = (await db.execute(expiring_q)).scalar() or 0

    expired_q = select(func.count(HomeAccessEntitlementModel.id)).where(
        HomeAccessEntitlementModel.home_id == home_ctx.home_id,
        (HomeAccessEntitlementModel.status == "EXPIRED") | (
            (HomeAccessEntitlementModel.status == "ACTIVE") & (HomeAccessEntitlementModel.expires_at < now)
        )
    )
    expired_count = (await db.execute(expired_q)).scalar() or 0

    return ApiSuccessResponse(
        data=HomeAdminSummaryDTO(
            home_id=home.id,
            home_name=home.name,
            public_home_id=home.public_home_id or "OZH-UNKNOWN",
            qr_status=home.home_qr_status or "ACTIVE",
            join_policy=getattr(home, "join_policy", "REQUEST_TO_JOIN") or "REQUEST_TO_JOIN",
            active_members_count=mem_count,
            pending_invitations_count=inv_count,
            pending_join_requests_count=req_count,
            expiring_access_count=expiring_count,
            expired_access_count=expired_count
        )
    )


@router.post("/homes/{home_id}/leave", response_model=ApiSuccessResponse[MessageResponse])
async def leave_home_workspace(
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Voluntarily leave a Home workspace.
    Invariant: Workspace Owner cannot leave without transferring ownership or deleting the workspace.
    """
    if home_ctx.role == "OWNER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The workspace Owner cannot leave the Home. You must transfer ownership or delete the workspace."
        )

    query = select(HomeMemberModel).where(
        HomeMemberModel.home_id == home_ctx.home_id,
        HomeMemberModel.user_id == home_ctx.user.id,
        HomeMemberModel.status == "ACTIVE"
    )
    member = (await db.execute(query)).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active membership not found.")

    member.status = "LEFT"
    member.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME_MEMBER",
        entity_id=member.id,
        action="MEMBER_LEFT",
        performed_by=home_ctx.user.id,
        details=json.dumps({"home_id": str(home_ctx.home_id), "user_id": str(home_ctx.user.id), "role": member.role})
    )
    db.add(audit)
    await db.commit()

    try:
        await redis_client.delete(f"user:{home_ctx.user.id}:homes")
        await redis_client.delete(f"user:{home_ctx.user.id}:home:{home_ctx.home_id}:perms")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=MessageResponse(message="You have successfully left this Home workspace.")
    )


# ------------------------------------------------------------------------------
# 2. Invitation Management
# ------------------------------------------------------------------------------

@router.post("/homes/{home_id}/invitations", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[InvitationDTO])
async def create_invitation(
    payload: CreateInvitationRequest,
    home_ctx: HomeContext = Depends(require_home_permission("members:invite")),
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    # 1. Enforce member seat limit before issuing invitation
    await check_home_member_seat_limit(home_ctx.home_id, db, include_pending=True)

    normalized_phone = None
    if payload.phone_number:
        normalized_phone = normalize_phone_number(payload.phone_number)

    normalized_email = payload.email.lower().strip() if payload.email else None

    # Check if target is already an active member of this home
    if normalized_email or normalized_phone:
        existing_mem_query = (
            select(HomeMemberModel)
            .join(UserModel, HomeMemberModel.user_id == UserModel.id)
            .where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )
        if normalized_email:
            existing_mem_query = existing_mem_query.where(UserModel.email == normalized_email)
        elif normalized_phone:
            existing_mem_query = existing_mem_query.where(UserModel.phone_number == normalized_phone)

        try:
            mem_res = await db.execute(existing_mem_query)
            existing_member = mem_res.scalar_one_or_none() if hasattr(mem_res, "scalar_one_or_none") else None
        except Exception:
            existing_member = None

        if isinstance(existing_member, HomeMemberModel):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user is already an active member of this Home."
            )

    token = secrets.token_urlsafe(24)
    invitation_code = generate_invitation_code()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    now = datetime.now(timezone.utc)

    new_invite = InvitationModel(
        id=uuid4(),
        home_id=home_ctx.home_id,
        phone_number=normalized_phone,
        email=normalized_email,
        role=payload.role,
        invitation_mode=payload.invitation_mode,
        token=token,
        invitation_code=invitation_code,
        invited_by=home_ctx.user.id,
        status="PENDING",
        expires_at=expires_at,
        created_at=now,
        updated_at=now
    )
    db.add(new_invite)

    # 1b. If invitation mode is with subscription, reserve entitlement seat
    if payload.invitation_mode == "INVITE_WITH_SUBSCRIPTION":
        target_type = "EMAIL" if normalized_email else "PHONE"
        target_val = normalized_email or normalized_phone
        if target_val:
            await reserve_home_access_entitlement(
                home_id=home_ctx.home_id,
                admin_user_id=home_ctx.user.id,
                identifier_type=target_type,
                identifier_value=target_val,
                subscription_id=None,
                db=db,
                notes=f"Reserved seat via invitation {invitation_code}"
            )

    # 2. Fetch Home details
    try:
        home = await db.get(HomeModel, home_ctx.home_id)
        home_name = home.name if (isinstance(home, HomeModel) and isinstance(home.name, str)) else "Home"
    except Exception:
        home_name = "Home"

    # 3. Check if invited user exists in Ozhzo and dispatch in-app notification
    existing_user = None
    try:
        if normalized_email:
            user_res = await db.execute(select(UserModel).where(UserModel.email == normalized_email, UserModel.deleted_at == None))
            fetched_u = user_res.scalar_one_or_none() if hasattr(user_res, "scalar_one_or_none") else None
            if isinstance(fetched_u, UserModel):
                existing_user = fetched_u
        elif normalized_phone:
            user_res = await db.execute(select(UserModel).where(UserModel.phone_number == normalized_phone, UserModel.deleted_at == None))
            fetched_u = user_res.scalar_one_or_none() if hasattr(user_res, "scalar_one_or_none") else None
            if isinstance(fetched_u, UserModel):
                existing_user = fetched_u
    except Exception:
        existing_user = None

    if existing_user and existing_user.id != home_ctx.user.id:
        inviter_name = home_ctx.user.email.split("@")[0] if home_ctx.user.email else "Home Admin"
        try:
            profile_res = await db.execute(select(UserProfileModel).where(UserProfileModel.user_id == home_ctx.user.id))
            prof = profile_res.scalar_one_or_none()
            if prof and prof.display_name:
                inviter_name = prof.display_name
        except Exception:
            pass

        try:
            reserved_suffix = " Subscription reserved for you." if getattr(new_invite, "is_reserved", False) else ""
            await notification_service.dispatch(
                home_id=home_ctx.home_id,
                user_id=existing_user.id,
                title=f"Invitation to join {home_name}",
                body=f"{inviter_name} invited you to join '{home_name}' as a {payload.role}.{reserved_suffix}",
                type="HOME_INVITATION",
                db=db,
                redis_client=redis_client,
                priority="HIGH",
                requires_action=True,
                action_type="JOIN_HOME",
                action_url=f"/invite/{token}",
                action_label="Accept / Decline",
                dedup_key=f"inv_received_{new_invite.id}",
                metadata={
                    "invitation_id": str(new_invite.id),
                    "token": token,
                    "invitation_code": invitation_code,
                    "home_id": str(home_ctx.home_id),
                    "home_name": home_name,
                    "role": payload.role,
                    "is_reserved": getattr(new_invite, "is_reserved", False)
                }
            )
        except Exception:
            pass

    # 4. Audit Log
    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=new_invite.id,
        action="INVITATION_CREATED",
        performed_by=home_ctx.user.id,
        details=json.dumps({
            "home_id": str(home_ctx.home_id),
            "phone_number": normalized_phone,
            "email": normalized_email,
            "role": payload.role,
            "mode": payload.invitation_mode,
            "invitation_code": invitation_code
        })
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(
        data=InvitationDTO(
            id=new_invite.id,
            home_id=new_invite.home_id,
            home_name=home_name,
            phone_number=new_invite.phone_number,
            email=new_invite.email,
            role=new_invite.role,
            invitation_mode=new_invite.invitation_mode,
            token=new_invite.token,
            invitation_code=new_invite.invitation_code,
            invite_url=f"/invite/{new_invite.token}",
            status=new_invite.status,
            invited_by=new_invite.invited_by,
            invited_by_name=home_ctx.user.email.split("@")[0] if home_ctx.user.email else "Home Admin",
            expires_at=new_invite.expires_at,
            created_at=new_invite.created_at
        )
    )


@router.get("/homes/{home_id}/invitations", response_model=ApiSuccessResponse[List[InvitationDTO]])
async def list_home_invitations(
    status: Optional[str] = "PENDING",
    search: Optional[str] = None,
    home_ctx: HomeContext = Depends(require_home_permission("members:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(InvitationModel, HomeModel.name, UserModel.email, UserProfileModel.display_name)
        .join(HomeModel, InvitationModel.home_id == HomeModel.id)
        .outerjoin(UserModel, InvitationModel.invited_by == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(InvitationModel.home_id == home_ctx.home_id)
    )

    if status and status.upper() != "ALL":
        query = query.where(InvitationModel.status == status.upper())

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(InvitationModel.email).like(s) |
            InvitationModel.phone_number.like(s) |
            func.lower(InvitationModel.invitation_code).like(s)
        )

    query = query.order_by(InvitationModel.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    invitations = []
    for inv, home_name, inv_email, inv_disp in rows:
        if not inv.invitation_code:
            inv.invitation_code = generate_invitation_code()
            db.add(inv)

        invitations.append(
            InvitationDTO(
                id=inv.id,
                home_id=inv.home_id,
                home_name=home_name,
                phone_number=inv.phone_number,
                email=inv.email,
                role=inv.role,
                invitation_mode=getattr(inv, "invitation_mode", "INVITE_ONLY") or "INVITE_ONLY",
                token=inv.token,
                invitation_code=inv.invitation_code,
                invite_url=f"/invite/{inv.token}",
                status=inv.status,
                invited_by=inv.invited_by,
                invited_by_name=inv_disp or (inv_email.split("@")[0] if inv_email else "Home Admin"),
                expires_at=inv.expires_at,
                created_at=inv.created_at
            )
        )

    await db.commit()
    return ApiSuccessResponse(data=invitations)


@router.delete("/homes/{home_id}/invitations/{invitation_id}", response_model=ApiSuccessResponse[MessageResponse])
async def cancel_home_invitation(
    invitation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("members:invite")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InvitationModel).where(
        InvitationModel.id == invitation_id,
        InvitationModel.home_id == home_ctx.home_id
    )
    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if inv.status == "ACCEPTED":
        raise HTTPException(status_code=400, detail="Cannot cancel an invitation that has already been accepted.")

    inv.status = "REVOKED"
    inv.revoked_at = datetime.now(timezone.utc)
    inv.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=inv.id,
        action="INVITATION_REVOKED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"home_id": str(home_ctx.home_id), "email": inv.email, "phone_number": inv.phone_number, "invitation_code": inv.invitation_code})
    )
    db.add(audit)
    # Auto-resolve pending recipient alert
    await notification_service.resolve_by_dedup_prefix(f"inv_received_{inv.id}", db)
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Invitation has been cancelled and revoked."))


@router.post("/homes/{home_id}/invitations/{invitation_id}/resend", response_model=ApiSuccessResponse[InvitationDTO])
async def resend_home_invitation(
    invitation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("members:invite")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InvitationModel).where(
        InvitationModel.id == invitation_id,
        InvitationModel.home_id == home_ctx.home_id
    )
    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if inv.status == "ACCEPTED":
        raise HTTPException(status_code=400, detail="Cannot resend an invitation that has already been accepted.")

    # Refresh token & code, extend expiry by 7 days
    inv.token = secrets.token_urlsafe(24)
    inv.invitation_code = generate_invitation_code()
    inv.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    inv.status = "PENDING"
    inv.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=inv.id,
        action="INVITATION_RESENT",
        performed_by=home_ctx.user.id,
        details=json.dumps({"home_id": str(home_ctx.home_id), "email": inv.email, "phone_number": inv.phone_number, "invitation_code": inv.invitation_code})
    )
    db.add(audit)
    await db.commit()

    home = await db.get(HomeModel, home_ctx.home_id)
    home_name = home.name if home else "Home"

    return ApiSuccessResponse(
        data=InvitationDTO(
            id=inv.id,
            home_id=inv.home_id,
            home_name=home_name,
            phone_number=inv.phone_number,
            email=inv.email,
            role=inv.role or "MEMBER",
            invitation_mode=getattr(inv, "invitation_mode", "INVITE_ONLY") or "INVITE_ONLY",
            token=inv.token,
            invitation_code=inv.invitation_code,
            invite_url=f"/invite/{inv.token}",
            status=inv.status,
            invited_by=inv.invited_by,
            invited_by_name=home_ctx.user.email.split("@")[0] if home_ctx.user.email else "Home Admin",
            expires_at=inv.expires_at,
            created_at=inv.created_at
        ),
        message="Invitation link refreshed and expiry extended."
    )


# ------------------------------------------------------------------------------
# 3. Public / User Invitation Lookup & Join Flows
# ------------------------------------------------------------------------------

@router.get("/invitations/{token_or_code}", response_model=ApiSuccessResponse[InvitationDetailDTO])
async def get_invitation_details(
    token_or_code: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Look up invitation details by link token or human-readable invitation code.
    Accessible publicly so unauthenticated users can preview the invite before signing in.
    """
    clean_identifier = token_or_code.strip()
    query = (
        select(InvitationModel, HomeModel, UserModel, UserProfileModel)
        .join(HomeModel, InvitationModel.home_id == HomeModel.id)
        .outerjoin(UserModel, InvitationModel.invited_by == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(
            (InvitationModel.token == clean_identifier) |
            (func.upper(InvitationModel.invitation_code) == clean_identifier.upper())
        )
    )
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This invitation could not be found."
        )

    inv, home, inviter_user, inviter_prof = row

    now = datetime.now(timezone.utc)
    inv_exp = _normalize_utc_dt(inv.expires_at)
    is_expired = inv_exp < now if inv_exp else False
    if is_expired and inv.status == "PENDING":
        inv.status = "EXPIRED"
        await db.commit()

    inviter_name = inviter_prof.display_name if inviter_prof else (inviter_user.email.split("@")[0] if inviter_user and inviter_user.email else "A family member")

    # Check if currently authenticated user is already a member
    is_already_member = False
    is_identity_matched: Optional[bool] = None
    identity_mismatch_reason: Optional[str] = None

    opt_user = await _extract_optional_user(credentials, db)
    if opt_user:
        mem_query = select(HomeMemberModel).where(
            HomeMemberModel.home_id == home.id,
            HomeMemberModel.user_id == opt_user.id,
            HomeMemberModel.status == "ACTIVE"
        )
        mem = (await db.execute(mem_query)).scalar_one_or_none()
        if mem:
            is_already_member = True

        # Compute identity matching for authenticated user
        matched = True
        if inv.phone_number:
            opt_phone = opt_user.phone_number
            if not opt_phone and getattr(opt_user, "profile", None) and opt_user.profile.phone_number:
                opt_phone = opt_user.profile.phone_number

            if not opt_phone or not opt_user.mobile_verified:
                matched = False
                identity_mismatch_reason = "Please verify your mobile number before accepting this invitation."
            elif normalize_phone_number(opt_phone) != normalize_phone_number(inv.phone_number):
                matched = False
                identity_mismatch_reason = "This invitation was issued to a different mobile number."

        if inv.email and matched:
            if not opt_user.email or opt_user.email.lower().strip() != inv.email.lower().strip():
                matched = False
                identity_mismatch_reason = "This invitation was issued to a different email address."
            elif (hasattr(opt_user, "is_verified") and opt_user.is_verified is False) or (hasattr(opt_user, "email_verified") and opt_user.email_verified is False):
                matched = False
                identity_mismatch_reason = "Please verify your email address before accepting this invitation."

        is_identity_matched = matched

    return ApiSuccessResponse(
        data=InvitationDetailDTO(
            id=inv.id,
            home_id=home.id,
            home_name=home.name,
            role=inv.role,
            token=inv.token,
            invitation_code=inv.invitation_code,
            status=inv.status,
            invited_by_name=inviter_name,
            invited_by_email=inviter_user.email if inviter_user else None,
            email=inv.email,
            phone_number=inv.phone_number,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            is_expired=is_expired,
            is_already_member=is_already_member,
            is_identity_matched=is_identity_matched,
            identity_mismatch_reason=identity_mismatch_reason
        )
    )


async def _execute_join_invitation(
    token_or_code: str,
    current_user: UserModel,
    db: AsyncSession,
    redis_client: redis.Redis,
) -> AcceptInvitationResponse:
    """Core join execution verifying status, expiry, mobile verification, seat availability, and single-use."""
    clean_identifier = token_or_code.strip()

    query = (
        select(InvitationModel, HomeModel)
        .join(HomeModel, InvitationModel.home_id == HomeModel.id)
        .where(
            (InvitationModel.token == clean_identifier) |
            (func.upper(InvitationModel.invitation_code) == clean_identifier.upper())
        )
    )
    result = await db.execute(query)
    inv_data = result.first()

    if not inv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This invitation could not be found."
        )

    invitation, home = inv_data

    # 1. Validate home status
    if home.deleted_at is not None or getattr(home, "status", "ACTIVE") == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Home workspace for this invitation is unavailable or suspended."
        )

    # 2. Validate invitation status
    if invitation.status == "ACCEPTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been accepted."
        )
    if invitation.status in ["REVOKED", "DECLINED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has been revoked or cancelled."
        )

    # 3. Validate expiration
    now = datetime.now(timezone.utc)
    inv_exp = _normalize_utc_dt(invitation.expires_at)
    if inv_exp and inv_exp < now:
        invitation.status = "EXPIRED"
        invitation.updated_at = now
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired."
        )

    # 4. Enforce recipient constraints if issued to a specific mobile number or email
    if invitation.phone_number:
        user_phone = current_user.phone_number
        if not user_phone and getattr(current_user, "profile", None) and current_user.profile.phone_number:
            user_phone = current_user.profile.phone_number

        if not user_phone or not current_user.mobile_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your mobile number before accepting this invitation."
            )

        if normalize_phone_number(user_phone) != normalize_phone_number(invitation.phone_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different mobile number."
            )

    if invitation.email:
        if not current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different email address."
            )
        if current_user.email.lower().strip() != invitation.email.lower().strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different email address."
            )
        if (hasattr(current_user, "is_verified") and current_user.is_verified is False) or (hasattr(current_user, "email_verified") and current_user.email_verified is False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before accepting this invitation."
            )

    # 5. Check duplicate active membership
    mem_query = select(HomeMemberModel).where(
        HomeMemberModel.home_id == home.id,
        HomeMemberModel.user_id == current_user.id
    )
    existing_member = (await db.execute(mem_query)).scalar_one_or_none()

    if existing_member and existing_member.status == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this Home."
        )

    # 6. Enforce subscription member seat limits with concurrency locking
    await check_and_reserve_home_member_seat(home.id, db, include_pending_invitations=False, lock_home=True)

    # 7. Create or reactivate membership
    membership_status = "ACTIVE"
    if invitation.invitation_mode == "INVITE_WITH_SUBSCRIPTION":
        if not home.subscription or home.subscription.status not in ["ACTIVE", "TRIALING"]:
            membership_status = "PENDING_SUBSCRIPTION"

    if existing_member:
        existing_member.status = membership_status
        existing_member.role = invitation.role
        existing_member.updated_at = now
    else:
        new_membership = HomeMemberModel(
            id=uuid4(),
            home_id=home.id,
            user_id=current_user.id,
            role=invitation.role,
            status=membership_status,
            joined_at=now,
            created_at=now,
            updated_at=now
        )
        db.add(new_membership)

    # 7b. Claim or activate Access Entitlement for this joining user (Rule D & Rule E)
    claimed_ent = await claim_reserved_entitlement(current_user, home.id, db)
    if not claimed_ent and invitation.invitation_mode == "INVITE_WITH_SUBSCRIPTION":
        sub_id = home.subscription.id if (hasattr(home, "subscription") and home.subscription) else None
        await provision_paid_home_entitlement(current_user, home, sub_id, db)

    # 8. Mark invitation as ACCEPTED (single-use)
    invitation.status = "ACCEPTED"
    invitation.accepted_by = current_user.id
    invitation.accepted_at = now
    invitation.updated_at = now

    # 9. Audit trail
    audit_invite = AuditLogModel(
        entity_type="INVITATION",
        entity_id=invitation.id,
        action="INVITATION_ACCEPTED",
        performed_by=current_user.id,
        details=json.dumps({
            "home_id": str(home.id),
            "role": invitation.role,
            "invitation_code": invitation.invitation_code
        })
    )
    audit_member = AuditLogModel(
        entity_type="HOME_MEMBER",
        entity_id=current_user.id,
        action="MEMBER_ADDED",
        performed_by=current_user.id,
        details=json.dumps({
            "home_id": str(home.id),
            "role": invitation.role
        })
    )
    db.add(audit_invite)
    db.add(audit_member)

    # 10. Notify inviter / home owner
    if invitation.invited_by and invitation.invited_by != current_user.id:
        user_name = current_user.email.split("@")[0] if current_user.email else "A family member"
        try:
            prof_res = await db.execute(select(UserProfileModel).where(UserProfileModel.user_id == current_user.id))
            p = prof_res.scalar_one_or_none()
            if p and p.display_name:
                user_name = p.display_name
        except Exception:
            pass

        try:
            await notification_service.dispatch(
                home_id=home.id,
                user_id=invitation.invited_by,
                title=f"New member joined {home.name}",
                body=f"{user_name} accepted your invitation and joined '{home.name}'.",
                type="INVITATION_ACCEPTED",
                priority="HIGH",
                requires_action=False,
                action_status="RESOLVED",
                db=db,
                redis_client=redis_client,
                metadata={"home_id": str(home.id), "user_id": str(current_user.id)}
            )
        except Exception:
            pass

    # Auto-resolve recipient's invitation notification
    await notification_service.resolve_by_dedup_prefix(f"inv_received_{invitation.id}", db)

    await db.commit()

    # Invalidate cache
    try:
        await redis_client.delete(f"user:{current_user.id}:homes")
        await redis_client.delete(f"user:{current_user.id}:home:{home.id}:perms")
    except Exception:
        pass

    return AcceptInvitationResponse(
        home_id=home.id,
        home_name=home.name,
        role=invitation.role,
        message=f"Welcome! You have joined '{home.name}' as a {invitation.role}."
    )


@router.post("/invitations/{token_or_code}/accept", response_model=ApiSuccessResponse[AcceptInvitationResponse])
async def accept_invitation(
    token_or_code: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    """Join Home via invitation link token or invitation code."""
    res = await _execute_join_invitation(token_or_code, current_user, db, redis_client)
    return ApiSuccessResponse(data=res)


@router.post("/homes/invitations/redeem", response_model=ApiSuccessResponse[AcceptInvitationResponse])
async def redeem_home_invitation_code(
    payload: RedeemInvitationRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    """Redeem a human-readable invitation code (e.g. OZ-XXXXXX) or token."""
    res = await _execute_join_invitation(payload.invitation_code, current_user, db, redis_client)
    return ApiSuccessResponse(data=res)


@router.post("/invitations/redeem", response_model=ApiSuccessResponse[AcceptInvitationResponse])
async def redeem_invitation_code_alias(
    payload: RedeemInvitationRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Alias for redeeming an invitation code."""
    res = await _execute_join_invitation(payload.invitation_code, current_user, db, redis_client)
    return ApiSuccessResponse(data=res)


@router.post("/invitations/{token_or_code}/decline", response_model=ApiSuccessResponse[MessageResponse])
async def decline_invitation(
    token_or_code: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clean_identifier = token_or_code.strip()
    query = select(InvitationModel).where(
        (InvitationModel.token == clean_identifier) |
        (func.upper(InvitationModel.invitation_code) == clean_identifier.upper())
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="This invitation could not be found.")

    if invitation.status != "PENDING":
        raise HTTPException(status_code=400, detail="This invitation is no longer pending.")

    invitation.status = "DECLINED"
    invitation.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=invitation.id,
        action="INVITATION_DECLINED",
        performed_by=current_user.id,
        details=json.dumps({"home_id": str(invitation.home_id), "invitation_code": invitation.invitation_code})
    )
    db.add(audit)

    # Auto-resolve recipient's invitation notification
    await notification_service.resolve_by_dedup_prefix(f"inv_received_{invitation.id}", db)

    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Invitation has been declined.")
    )
