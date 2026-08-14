import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.core.otp import normalize_phone_number
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AuditLogModel,
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    UserModel,
    UserProfileModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.common import ApiSuccessResponse
from src.schemas.home import (
    AcceptInvitationResponse,
    CreateInvitationRequest,
    InvitationDTO,
    MemberDTO,
    MessageResponse,
    UpdateMemberRoleRequest,
)

router = APIRouter(tags=["Home Members & Invitations"])


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

    if target_member.role in ["OWNER", "HOME_ADMIN"] and target_member.user_id != home_ctx.user.id:
        if home_ctx.role not in ["OWNER", "HOME_ADMIN"]:
            raise HTTPException(status_code=403, detail="Only a Home Admin can modify another Admin's role.")

    old_role = target_member.role
    target_member.role = payload.role
    target_member.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME_MEMBER",
        entity_id=target_member.id,
        action="ROLE_CHANGED",
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


@router.post("/homes/{home_id}/invitations", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[InvitationDTO])
async def create_invitation(
    payload: CreateInvitationRequest,
    home_ctx: HomeContext = Depends(require_home_permission("members:invite")),
    db: AsyncSession = Depends(get_db),
):
    normalized_phone = None
    if payload.phone_number:
        normalized_phone = normalize_phone_number(payload.phone_number)

    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    new_invite = InvitationModel(
        home_id=home_ctx.home_id,
        phone_number=normalized_phone,
        email=payload.email.lower() if payload.email else None,
        role=payload.role,
        invitation_mode=payload.invitation_mode,
        token=token,
        invited_by=home_ctx.user.id,
        status="PENDING",
        expires_at=expires_at
    )
    db.add(new_invite)

    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=new_invite.id,
        action="INVITATION_CREATED",
        performed_by=home_ctx.user.id,
        details=json.dumps({
            "home_id": str(home_ctx.home_id),
            "phone_number": normalized_phone,
            "email": payload.email,
            "role": payload.role,
            "mode": payload.invitation_mode
        })
    )
    db.add(audit)
    await db.commit()

    home = await db.get(HomeModel, home_ctx.home_id)
    home_name = home.name if home else "Home"

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
            invite_url=f"/join?token={new_invite.token}",
            status=new_invite.status,
            invited_by=new_invite.invited_by,
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
        select(InvitationModel, HomeModel.name)
        .join(HomeModel, InvitationModel.home_id == HomeModel.id)
        .where(
            InvitationModel.home_id == home_ctx.home_id,
            InvitationModel.status == "PENDING"
        )
        .order_by(InvitationModel.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    invitations = [
        InvitationDTO(
            id=inv.id,
            home_id=inv.home_id,
            home_name=home_name,
            phone_number=inv.phone_number,
            email=inv.email,
            role=inv.role,
            invitation_mode=inv.invitation_mode,
            token=inv.token,
            invite_url=f"/join?token={inv.token}",
            status=inv.status,
            invited_by=inv.invited_by,
            expires_at=inv.expires_at,
            created_at=inv.created_at
        )
        for inv, home_name in rows
    ]

    return ApiSuccessResponse(data=invitations)


@router.post("/invitations/{token}/accept", response_model=ApiSuccessResponse[AcceptInvitationResponse])
async def accept_invitation(
    token: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    if current_user.phone_number and not current_user.mobile_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mobile number verification is required before joining a Home."
        )

    query = select(InvitationModel, HomeModel).join(HomeModel, InvitationModel.home_id == HomeModel.id).where(
        InvitationModel.token == token,
        InvitationModel.status == "PENDING"
    )
    result = await db.execute(query)
    inv_data = result.first()

    if not inv_data:
        raise HTTPException(status_code=404, detail="Invitation link is invalid, expired, or already used.")

    invitation, home = inv_data

    # Check expiration
    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "EXPIRED"
        await db.commit()
        raise HTTPException(status_code=400, detail="This invitation link has expired.")

    # Security check: Transfer prevention if phone number bound
    if invitation.phone_number:
        if current_user.phone_number != invitation.phone_number:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different mobile number."
            )

    # Check existing membership
    mem_query = select(HomeMemberModel).where(
        HomeMemberModel.home_id == home.id,
        HomeMemberModel.user_id == current_user.id
    )
    existing_member = (await db.execute(mem_query)).scalar_one_or_none()

    if existing_member and existing_member.status == "ACTIVE":
        raise HTTPException(status_code=400, detail="You are already an active member of this Home.")

    membership_status = "ACTIVE"
    if invitation.invitation_mode == "INVITE_WITH_SUBSCRIPTION":
        # If Home has no active subscription, set to PENDING_SUBSCRIPTION
        if not home.subscription or home.subscription.status not in ["ACTIVE", "TRIALING"]:
            membership_status = "PENDING_SUBSCRIPTION"

    if existing_member:
        existing_member.status = membership_status
        existing_member.role = invitation.role
        existing_member.updated_at = datetime.now(timezone.utc)
    else:
        new_membership = HomeMemberModel(
            home_id=home.id,
            user_id=current_user.id,
            role=invitation.role,
            status=membership_status
        )
        db.add(new_membership)

    invitation.status = "ACCEPTED"
    invitation.accepted_by = current_user.id
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=invitation.id,
        action="INVITATION_ACCEPTED",
        performed_by=current_user.id,
        details=json.dumps({"home_id": str(home.id), "role": invitation.role})
    )
    db.add(audit)
    await db.commit()

    try:
        await redis_client.delete(f"user:{current_user.id}:homes")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=AcceptInvitationResponse(
            home_id=home.id,
            home_name=home.name,
            role=invitation.role,
            message=f"Welcome! You have joined '{home.name}' as a {invitation.role}."
        )
    )


@router.post("/invitations/{token}/decline", response_model=ApiSuccessResponse[MessageResponse])
async def decline_invitation(
    token: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(InvitationModel).where(
        InvitationModel.token == token,
        InvitationModel.status == "PENDING"
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation link is invalid or already resolved.")

    invitation.status = "REVOKED"
    invitation.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="INVITATION",
        entity_id=invitation.id,
        action="INVITATION_DECLINED",
        performed_by=current_user.id,
        details=json.dumps({"home_id": str(invitation.home_id)})
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Invitation has been declined.")
    )
