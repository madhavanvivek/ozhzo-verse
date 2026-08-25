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
    HomeModel,
    HomeMemberModel,
    InvitationModel,
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
    InvitationDTO,
    InvitationDetailDTO,
    MemberDTO,
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


async def check_home_member_seat_limit(home_id: UUID, db: AsyncSession):
    """Enforce member seat limits based on subscription plan allowance."""
    # 1. Count active members and pending invitations
    allocated_count = 0
    try:
        active_count_query = select(func.count(HomeMemberModel.id)).where(
            HomeMemberModel.home_id == home_id,
            HomeMemberModel.status == "ACTIVE"
        )
        cnt_res = await db.execute(active_count_query)
        val = cnt_res.scalar() if hasattr(cnt_res, "scalar") else getattr(cnt_res, "scalar_one", lambda: 0)()
        if isinstance(val, int):
            allocated_count += val

        pending_count_query = select(func.count(InvitationModel.id)).where(
            InvitationModel.home_id == home_id,
            InvitationModel.status == "PENDING"
        )
        p_res = await db.execute(pending_count_query)
        p_val = p_res.scalar() if hasattr(p_res, "scalar") else getattr(p_res, "scalar_one", lambda: 0)()
        if isinstance(p_val, int):
            allocated_count += p_val
    except Exception:
        allocated_count = 0

    # 2. Query subscription if any
    sub_query = (
        select(SubscriptionModel)
        .options(selectinload(SubscriptionModel.plan))
        .where(SubscriptionModel.home_id == home_id)
    )
    try:
        sub_res = await db.execute(sub_query)
        sub = sub_res.scalar_one_or_none() if hasattr(sub_res, "scalar_one_or_none") else None
    except Exception:
        sub = None

    if isinstance(sub, SubscriptionModel) and sub.status in ["ACTIVE", "TRIALING"]:
        included = sub.plan.included_members if (sub.plan and hasattr(sub.plan, "included_members")) else 5
        paid_seats = sub.paid_member_seats or 0
        total_allowed = included + paid_seats
        if sub.plan and getattr(sub.plan, "maximum_members", None) and total_allowed > sub.plan.maximum_members:
            total_allowed = sub.plan.maximum_members
    else:
        # Default Free Tier allowance
        total_allowed = 5

    if allocated_count >= total_allowed:
        from src.core.exceptions import TierLimitExceededException
        raise TierLimitExceededException(
            resource="members",
            limit=total_allowed,
            detail="Your Home subscription does not have an available member seat."
        )


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
        user = await db.get(UserModel, user_id)
        return user if (user and user.is_active and user.deleted_at is None) else None
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 1. Member Management
# ------------------------------------------------------------------------------

@router.get("/homes/{home_id}/members", response_model=ApiSuccessResponse[List[MemberDTO]])
async def list_home_members(
    home_ctx: HomeContext = Depends(require_home_permission("members:view")),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(HomeMemberModel, UserModel, UserProfileModel)
        .join(UserModel, HomeMemberModel.user_id == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.status == "ACTIVE"
        )
        .order_by(HomeMemberModel.joined_at.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    members_dto = []
    for member, user, profile in rows:
        display_name = profile.display_name if profile else (user.email.split("@")[0] if user.email else user.phone_number or "Member")
        avatar_url = profile.avatar_url if profile else None
        phone_number = user.phone_number or (profile.phone_number if profile else None)
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
                joined_at=member.joined_at
            )
        )

    return ApiSuccessResponse(data=members_dto)


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

    if target_member.role == "OWNER" and target_member.user_id != home_ctx.user.id:
        raise HTTPException(status_code=400, detail="Cannot modify the role of the workspace Owner.")

    if target_member.role in ["OWNER", "HOME_ADMIN"] and target_member.user_id != home_ctx.user.id:
        if home_ctx.role not in ["OWNER", "HOME_ADMIN"]:
            raise HTTPException(status_code=403, detail="Only a Home Admin can modify another Admin's role.")

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

    if target_member.role == "OWNER":
        raise HTTPException(status_code=400, detail="Cannot remove the Home workspace Owner.")

    if target_member.role in ["OWNER", "HOME_ADMIN"] and target_member.user_id != home_ctx.user.id:
        if home_ctx.role not in ["OWNER", "HOME_ADMIN"]:
            raise HTTPException(status_code=403, detail="Only a Home Admin can remove another Admin.")

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
    await check_home_member_seat_limit(home_ctx.home_id, db)

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
            await notification_service.dispatch(
                home_id=home_ctx.home_id,
                user_id=existing_user.id,
                title=f"Invitation to join {home_name}",
                body=f"{inviter_name} invited you to join '{home_name}' as a {payload.role}.",
                type="HOME_INVITATION",
                db=db,
                redis_client=redis_client,
                metadata={
                    "invitation_id": str(new_invite.id),
                    "token": token,
                    "invitation_code": invitation_code,
                    "home_id": str(home_ctx.home_id),
                    "home_name": home_name,
                    "role": payload.role
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
    home_ctx: HomeContext = Depends(require_home_permission("members:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(InvitationModel, HomeModel.name, UserModel.email, UserProfileModel.display_name)
        .join(HomeModel, InvitationModel.home_id == HomeModel.id)
        .outerjoin(UserModel, InvitationModel.invited_by == UserModel.id)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(
            InvitationModel.home_id == home_ctx.home_id,
            InvitationModel.status == "PENDING"
        )
        .order_by(InvitationModel.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    invitations = []
    for inv, home_name, inv_email, inv_disp in rows:
        # Check if code exists; if legacy invitation has no code, assign one
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
        InvitationModel.home_id == home_ctx.home_id,
        InvitationModel.status == "PENDING"
    )
    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=404, detail="Pending invitation not found.")

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
        InvitationModel.home_id == home_ctx.home_id,
        InvitationModel.status == "PENDING"
    )
    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=404, detail="Pending invitation not found.")

    # Refresh token & code, extend expiry by 7 days
    inv.token = secrets.token_urlsafe(24)
    inv.invitation_code = generate_invitation_code()
    inv.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
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
            role=inv.role,
            invitation_mode=inv.invitation_mode,
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
    is_expired = inv.expires_at < now
    if is_expired and inv.status == "PENDING":
        inv.status = "EXPIRED"
        await db.commit()

    inviter_name = inviter_prof.display_name if inviter_prof else (inviter_user.email.split("@")[0] if inviter_user and inviter_user.email else "A family member")

    # Check if currently authenticated user is already a member
    is_already_member = False
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
            is_already_member=is_already_member
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
    if invitation.expires_at < now:
        invitation.status = "EXPIRED"
        invitation.updated_at = now
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired."
        )

    # 4. Enforce phone constraint if issued to a specific mobile number
    if invitation.phone_number and current_user.phone_number:
        if normalize_phone_number(current_user.phone_number) != normalize_phone_number(invitation.phone_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different mobile number."
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

    # 6. Enforce subscription member seat limits
    try:
        await check_home_member_seat_limit(home.id, db)
    except (HTTPException, BaseDomainException):
        raise
    except Exception:
        pass

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
                type="HOME_INVITATION",
                db=db,
                redis_client=redis_client,
                metadata={"home_id": str(home.id), "user_id": str(current_user.id)}
            )
        except Exception:
            pass

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
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Invitation has been declined.")
    )
