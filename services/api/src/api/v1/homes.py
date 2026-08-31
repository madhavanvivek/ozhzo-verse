import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AuditLogModel,
    HomeModel,
    HomeMemberModel,
    HomeJoinRequestModel,
    InventoryCategoryModel,
    InventoryItemModel,
    NotificationModel,
    SubscriptionModel,
    TaskModel,
    UserModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.domain.entitlements import check_can_create_home, check_and_reserve_home_member_seat
from src.core.exceptions import TierLimitExceededException, MobileVerificationRequiredException
from src.core.home_identity import generate_unique_public_home_id, generate_home_qr_token
from src.schemas.common import ApiSuccessResponse
from src.schemas.home import (
    CreateHomeRequest,
    CreateJoinRequestInput,
    HomeDTO,
    HomeDetailDTO,
    HomeIdentityDTO,
    HomePublicInfoDTO,
    JoinRequestDTO,
    MessageResponse,
    ReviewJoinRequestInput,
    UpdateHomeRequest
)

router = APIRouter(prefix="/homes", tags=["Homes"])


@router.get("", response_model=ApiSuccessResponse[List[HomeDTO]])
async def list_user_homes(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(HomeModel, HomeMemberModel.role)
        .join(HomeMemberModel, HomeModel.id == HomeMemberModel.home_id)
        .where(
            HomeMemberModel.user_id == current_user.id,
            HomeMemberModel.status == "ACTIVE",
            HomeModel.deleted_at.is_(None)
        )
        .order_by(HomeModel.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return ApiSuccessResponse(
        data=[
            HomeDTO(
                id=home.id,
                name=home.name,
                public_home_id=home.public_home_id,
                home_qr_status=home.home_qr_status or "ACTIVE",
                home_qr_version=home.home_qr_version or 1,
                home_qr_url=f"/join/home/{home.home_qr_token}" if home.home_qr_token else None,
                country=home.country,
                state_province=home.state_province,
                district_city=home.district_city,
                postal_code=home.postal_code,
                currency=home.currency or "USD",
                timezone=home.timezone or "UTC",
                address=home.address,
                avatar_url=home.avatar_url,
                created_by=home.created_by,
                role=role,
                created_at=home.created_at,
                updated_at=home.updated_at
            )
            for home, role in rows
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[HomeDTO])
async def create_home(
    payload: CreateHomeRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    if not current_user.mobile_verified:
        raise MobileVerificationRequiredException()

    # Enforce Home creation entitlement: 1 free home for regular users, subscription required for additional
    await check_can_create_home(current_user, db)

    # Generate permanent collision-resistant public Home ID and secure QR token
    public_id = await generate_unique_public_home_id(db)
    qr_token = generate_home_qr_token()

    # Mark user's lifetime free home grant as consumed
    current_user.free_home_consumed = True

    # 1. Create Home record
    new_home = HomeModel(
        id=uuid.uuid4(),
        name=payload.name,
        public_home_id=public_id,
        home_qr_token=qr_token,
        home_qr_status="ACTIVE",
        home_qr_version=1,
        home_qr_created_at=datetime.now(timezone.utc),
        country=payload.country,
        state_province=payload.state_province,
        district_city=payload.district_city,
        postal_code=payload.postal_code,
        currency=payload.currency,
        timezone=payload.timezone,
        address=payload.address,
        avatar_url=payload.avatar_url,
        created_by=current_user.id
    )
    db.add(new_home)
    await db.flush()

    # 2. Add creator automatically as HOME_ADMIN
    new_membership = HomeMemberModel(
        id=uuid.uuid4(),
        home_id=new_home.id,
        user_id=current_user.id,
        role="HOME_ADMIN",
        status="ACTIVE"
    )
    db.add(new_membership)

    # 3. Seed default inventory categories
    default_categories = [
        ("Pantry", "cookie"),
        ("Fridge", "refrigerator"),
        ("Freezer", "snowflake"),
        ("Cleaning", "sparkles"),
        ("Medicine", "pill"),
        ("Other", "package")
    ]
    for cat_name, icon in default_categories:
        db.add(InventoryCategoryModel(
            home_id=new_home.id,
            name=cat_name,
            icon=icon
        ))

    # 4. Audit Log
    audit = AuditLogModel(
        entity_type="HOME",
        entity_id=new_home.id,
        action="HOME_CREATED",
        performed_by=current_user.id,
        details=json.dumps({"name": new_home.name, "public_home_id": public_id, "country": new_home.country})
    )
    db.add(audit)

    await db.commit()

    try:
        await redis_client.delete(f"user:{current_user.id}:homes")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=HomeDTO(
            id=new_home.id,
            name=new_home.name,
            public_home_id=new_home.public_home_id,
            home_qr_status=new_home.home_qr_status,
            home_qr_version=new_home.home_qr_version,
            home_qr_url=f"/join/home/{new_home.home_qr_token}",
            country=new_home.country,
            state_province=new_home.state_province,
            district_city=new_home.district_city,
            postal_code=new_home.postal_code,
            currency=new_home.currency,
            timezone=new_home.timezone,
            address=new_home.address,
            avatar_url=new_home.avatar_url,
            created_by=new_home.created_by,
            role="HOME_ADMIN",
            created_at=new_home.created_at,
            updated_at=new_home.updated_at
        )
    )


# ------------------------------------------------------------------------------
# Public QR Discovery & Join Request Endpoints
# ------------------------------------------------------------------------------

@router.get("/public/resolve-qr/{token}", response_model=ApiSuccessResponse[HomePublicInfoDTO])
async def resolve_home_qr(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(HomeModel)
        .options(joinedload(HomeModel.members))
        .where(
            HomeModel.home_qr_token == token,
            HomeModel.deleted_at.is_(None)
        )
    )
    res = await db.execute(query)
    home = res.scalars().first()

    if not home or home.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home workspace not found or is inactive."
        )

    if home.home_qr_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Home QR code has been revoked or is no longer active."
        )

    # Owner display name
    owner_q = select(UserModel).where(UserModel.id == home.created_by)
    owner_res = await db.execute(owner_q)
    owner = owner_res.scalars().first()
    owner_name = owner.profile.display_name if owner and owner.profile and owner.profile.display_name else (
        owner.email if owner else "Household Administrator"
    )

    # Active member count
    active_members = [m for m in (home.members or []) if m.status == "ACTIVE"]

    return ApiSuccessResponse(
        data=HomePublicInfoDTO(
            home_id=home.id,
            home_name=home.name,
            public_home_id=home.public_home_id or "OZH-UNKNOWN",
            owner_name=owner_name,
            member_count=len(active_members),
            qr_status=home.home_qr_status,
            is_active=True,
            accepts_members=True,
            is_already_member=False,
            user_membership_status=None,
            has_pending_join_request=False
        )
    )


@router.post("/public/join-request/{token}", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[JoinRequestDTO])
async def create_join_request(
    token: str,
    payload: CreateJoinRequestInput,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Resolve Home
    query = select(HomeModel).where(
        HomeModel.home_qr_token == token,
        HomeModel.deleted_at.is_(None)
    )
    res = await db.execute(query)
    home = res.scalars().first()

    if not home or home.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home workspace not found.")

    if home.home_qr_status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This Home QR code has been revoked.")

    # 2. Check if already active member
    mem_q = select(HomeMemberModel).where(
        HomeMemberModel.home_id == home.id,
        HomeMemberModel.user_id == current_user.id,
        HomeMemberModel.status == "ACTIVE"
    )
    existing_mem = (await db.execute(mem_q)).scalars().first()
    if existing_mem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already an active member of this home.")

    # 3. Check if duplicate pending join request exists
    req_q = select(HomeJoinRequestModel).where(
        HomeJoinRequestModel.home_id == home.id,
        HomeJoinRequestModel.user_id == current_user.id,
        HomeJoinRequestModel.status == "PENDING"
    )
    existing_req = (await db.execute(req_q)).scalars().first()
    if existing_req:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already have a pending join request for this home.")

    # 4. Create Join Request
    join_req = HomeJoinRequestModel(
        id=uuid.uuid4(),
        home_id=home.id,
        user_id=current_user.id,
        status="PENDING",
        message=payload.message.strip() if payload.message else None,
        created_at=datetime.now(timezone.utc)
    )
    db.add(join_req)

    # 5. Notify Home Admins
    admins_q = select(HomeMemberModel).where(
        HomeMemberModel.home_id == home.id,
        HomeMemberModel.role.in_(["HOME_ADMIN", "OWNER", "ADMIN"]),
        HomeMemberModel.status == "ACTIVE"
    )
    admins = (await db.execute(admins_q)).scalars().all()
    user_name = current_user.profile.display_name if current_user.profile and current_user.profile.display_name else current_user.email
    for adm in admins:
        notif = NotificationModel(
            id=uuid.uuid4(),
            home_id=home.id,
            user_id=adm.user_id,
            title="New Home Join Request",
            body=f"{user_name} has requested to join {home.name}.",
            type="JOIN_REQUEST",
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(notif)

    await db.commit()

    return ApiSuccessResponse(
        data=JoinRequestDTO(
            id=join_req.id,
            home_id=home.id,
            home_name=home.name,
            user_id=current_user.id,
            display_name=user_name,
            email=current_user.email,
            status="PENDING",
            message=join_req.message,
            created_at=join_req.created_at
        )
    )


# ------------------------------------------------------------------------------
# Home Admin QR & Identity Management Endpoints
# ------------------------------------------------------------------------------

@router.get("/{home_id}/identity", response_model=ApiSuccessResponse[HomeIdentityDTO])
async def get_home_identity(
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db)
):
    home = await db.get(HomeModel, home_ctx.home_id)
    if not home or home.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home workspace not found.")

    # Ensure public_home_id and home_qr_token exist
    if not home.public_home_id or not home.home_qr_token:
        if not home.public_home_id:
            home.public_home_id = await generate_unique_public_home_id(db)
        if not home.home_qr_token:
            home.home_qr_token = generate_home_qr_token()
        await db.commit()

    return ApiSuccessResponse(
        data=HomeIdentityDTO(
            home_id=home.id,
            name=home.name,
            public_home_id=home.public_home_id,
            qr_token=home.home_qr_token,
            qr_status=home.home_qr_status or "ACTIVE",
            qr_version=home.home_qr_version or 1,
            qr_url=f"/join/home/{home.home_qr_token}",
            qr_created_at=home.home_qr_created_at,
            qr_revoked_at=home.home_qr_revoked_at
        )
    )


@router.post("/{home_id}/qr/regenerate", response_model=ApiSuccessResponse[HomeIdentityDTO])
async def regenerate_home_qr(
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db)
):
    home = await db.get(HomeModel, home_ctx.home_id)
    if not home or home.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home workspace not found.")

    old_token = home.home_qr_token
    new_token = generate_home_qr_token()

    home.home_qr_token = new_token
    home.home_qr_status = "ACTIVE"
    home.home_qr_version = (home.home_qr_version or 1) + 1
    home.home_qr_created_at = datetime.now(timezone.utc)
    home.home_qr_revoked_at = None

    audit = AuditLogModel(
        entity_type="HOME",
        entity_id=home.id,
        action="HOME_QR_REGENERATED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"version": home.home_qr_version})
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(
        data=HomeIdentityDTO(
            home_id=home.id,
            name=home.name,
            public_home_id=home.public_home_id or "OZH-UNKNOWN",
            qr_token=home.home_qr_token,
            qr_status=home.home_qr_status,
            qr_version=home.home_qr_version,
            qr_url=f"/join/home/{home.home_qr_token}",
            qr_created_at=home.home_qr_created_at,
            qr_revoked_at=None
        )
    )


@router.post("/{home_id}/qr/revoke", response_model=ApiSuccessResponse[HomeIdentityDTO])
async def revoke_home_qr(
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db)
):
    home = await db.get(HomeModel, home_ctx.home_id)
    if not home or home.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home workspace not found.")

    home.home_qr_status = "REVOKED"
    home.home_qr_revoked_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME",
        entity_id=home.id,
        action="HOME_QR_REVOKED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"revoked_at": home.home_qr_revoked_at.isoformat()})
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(
        data=HomeIdentityDTO(
            home_id=home.id,
            name=home.name,
            public_home_id=home.public_home_id or "OZH-UNKNOWN",
            qr_token=home.home_qr_token or "",
            qr_status=home.home_qr_status,
            qr_version=home.home_qr_version or 1,
            qr_url=f"/join/home/{home.home_qr_token}" if home.home_qr_token else "",
            qr_created_at=home.home_qr_created_at,
            qr_revoked_at=home.home_qr_revoked_at
        )
    )


@router.get("/{home_id}/join-requests", response_model=ApiSuccessResponse[List[JoinRequestDTO]])
async def list_home_join_requests(
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(HomeJoinRequestModel)
        .options(joinedload(HomeJoinRequestModel.user).joinedload(UserModel.profile))
        .where(
            HomeJoinRequestModel.home_id == home_ctx.home_id
        )
        .order_by(HomeJoinRequestModel.created_at.desc())
    )
    res = await db.execute(query)
    requests = res.scalars().all()

    items: List[JoinRequestDTO] = []
    for r in requests:
        user_name = r.user.profile.display_name if r.user and r.user.profile and r.user.profile.display_name else (
            r.user.email if r.user else "User"
        )
        items.append(
            JoinRequestDTO(
                id=r.id,
                home_id=r.home_id,
                user_id=r.user_id,
                display_name=user_name,
                email=r.user.email if r.user else None,
                avatar_url=r.user.profile.avatar_url if r.user and r.user.profile else None,
                status=r.status,
                message=r.message,
                created_at=r.created_at,
                reviewed_by=r.reviewed_by,
                reviewed_at=r.reviewed_at
            )
        )

    return ApiSuccessResponse(data=items)


@router.post("/{home_id}/join-requests/{request_id}/review", response_model=ApiSuccessResponse[JoinRequestDTO])
async def review_join_request(
    request_id: UUID,
    payload: ReviewJoinRequestInput,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    join_req = await db.get(HomeJoinRequestModel, request_id)
    if not join_req or join_req.home_id != home_ctx.home_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found.")

    if join_req.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Join request has already been reviewed.")

    if payload.action == "APPROVE":
        # Enforce subscription member limit with concurrency locking
        await check_and_reserve_home_member_seat(home_ctx.home_id, db, lock_home=True)

        # Check if membership already exists (e.g. previously removed or inactive)
        existing_mem_q = select(HomeMemberModel).where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.user_id == join_req.user_id
        )
        existing_mem_res = await db.execute(existing_mem_q)
        existing_mem = existing_mem_res.scalar_one_or_none() if hasattr(existing_mem_res, "scalar_one_or_none") else None

        if existing_mem:
            existing_mem.status = "ACTIVE"
            existing_mem.role = payload.role or "MEMBER"
            existing_mem.updated_at = datetime.now(timezone.utc)
        else:
            new_mem = HomeMemberModel(
                id=uuid.uuid4(),
                home_id=home_ctx.home_id,
                user_id=join_req.user_id,
                role=payload.role or "MEMBER",
                status="ACTIVE",
                joined_at=datetime.now(timezone.utc)
            )
            db.add(new_mem)

        join_req.status = "APPROVED"
        join_req.reviewed_by = home_ctx.user.id
        join_req.reviewed_at = datetime.now(timezone.utc)

        # Notify user
        notif = NotificationModel(
            id=uuid.uuid4(),
            home_id=home_ctx.home_id,
            user_id=join_req.user_id,
            title="Join Request Approved!",
            body=f"Your request to join {home_ctx.home.name if hasattr(home_ctx, 'home') and home_ctx.home else 'the home'} has been approved.",
            type="JOIN_REQUEST_APPROVED",
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(notif)

        try:
            await redis_client.delete(f"user:{join_req.user_id}:homes")
        except Exception:
            pass

    elif payload.action == "REJECT":
        join_req.status = "REJECTED"
        join_req.reviewed_by = home_ctx.user.id
        join_req.reviewed_at = datetime.now(timezone.utc)

        # Notify user
        notif = NotificationModel(
            id=uuid.uuid4(),
            home_id=home_ctx.home_id,
            user_id=join_req.user_id,
            title="Join Request Update",
            body=f"Your request to join the home was not accepted.",
            type="JOIN_REQUEST_REJECTED",
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(notif)

    await db.commit()

    return ApiSuccessResponse(
        data=JoinRequestDTO(
            id=join_req.id,
            home_id=join_req.home_id,
            user_id=join_req.user_id,
            display_name="Applicant",
            status=join_req.status,
            message=join_req.message,
            created_at=join_req.created_at or datetime.now(timezone.utc),
            reviewed_by=join_req.reviewed_by,
            reviewed_at=join_req.reviewed_at or datetime.now(timezone.utc)
        )
    )


# ------------------------------------------------------------------------------
# Standard Home Details, Update & Delete
# ------------------------------------------------------------------------------

@router.get("/{home_id}", response_model=ApiSuccessResponse[HomeDetailDTO])
async def get_home_details(
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db)
):
    query = select(HomeModel).where(
        HomeModel.id == home_ctx.home_id,
        HomeModel.deleted_at.is_(None)
    )
    result = await db.execute(query)
    home = result.scalar_one_or_none()

    if not home:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    members_count_query = select(func.count()).select_from(HomeMemberModel).where(
        HomeMemberModel.home_id == home_ctx.home_id,
        HomeMemberModel.status == "ACTIVE"
    )
    members_count = (await db.execute(members_count_query)).scalar() or 1

    inventory_count_query = select(func.count()).select_from(InventoryItemModel).where(
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at.is_(None)
    )
    inventory_count = (await db.execute(inventory_count_query)).scalar() or 0

    chores_count_query = select(func.count()).select_from(TaskModel).where(
        TaskModel.home_id == home_ctx.home_id,
        TaskModel.status.in_(["TODO", "IN_PROGRESS"]),
        TaskModel.deleted_at.is_(None)
    )
    chores_count = (await db.execute(chores_count_query)).scalar() or 0

    return ApiSuccessResponse(
        data=HomeDetailDTO(
            id=home.id,
            name=home.name,
            public_home_id=home.public_home_id,
            home_qr_status=home.home_qr_status or "ACTIVE",
            home_qr_version=home.home_qr_version or 1,
            home_qr_url=f"/join/home/{home.home_qr_token}" if home.home_qr_token else None,
            country=home.country,
            state_province=home.state_province,
            district_city=home.district_city,
            postal_code=home.postal_code,
            currency=home.currency,
            timezone=home.timezone,
            address=home.address,
            avatar_url=home.avatar_url,
            created_by=home.created_by,
            role=home_ctx.role,
            member_count=members_count,
            inventory_count=inventory_count,
            active_chores_count=chores_count,
            created_at=home.created_at,
            updated_at=home.updated_at
        )
    )


@router.patch("/{home_id}", response_model=ApiSuccessResponse[HomeDTO])
async def update_home_settings(
    payload: UpdateHomeRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(HomeModel).where(
        HomeModel.id == home_ctx.home_id,
        HomeModel.deleted_at.is_(None)
    )
    result = await db.execute(query)
    home = result.scalar_one_or_none()

    if not home:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    if payload.name is not None:
        home.name = payload.name
    if payload.country is not None:
        home.country = payload.country
    if payload.state_province is not None:
        home.state_province = payload.state_province
    if payload.district_city is not None:
        home.district_city = payload.district_city
    if payload.postal_code is not None:
        home.postal_code = payload.postal_code
    if payload.currency is not None:
        home.currency = payload.currency
    if payload.timezone is not None:
        home.timezone = payload.timezone
    if payload.address is not None:
        home.address = payload.address
    if payload.avatar_url is not None:
        home.avatar_url = payload.avatar_url

    home.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME",
        entity_id=home.id,
        action="HOME_UPDATED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"name": home.name})
    )
    db.add(audit)
    await db.commit()

    try:
        await redis_client.delete(f"home:{home_ctx.home_id}:settings")
        await redis_client.delete(f"user:{home_ctx.user.id}:homes")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=HomeDTO(
            id=home.id,
            name=home.name,
            public_home_id=home.public_home_id,
            home_qr_status=home.home_qr_status or "ACTIVE",
            home_qr_version=home.home_qr_version or 1,
            home_qr_url=f"/join/home/{home.home_qr_token}" if home.home_qr_token else None,
            country=home.country,
            state_province=home.state_province,
            district_city=home.district_city,
            postal_code=home.postal_code,
            currency=home.currency,
            timezone=home.timezone,
            address=home.address,
            avatar_url=home.avatar_url,
            created_by=home.created_by,
            role=home_ctx.role,
            created_at=home.created_at,
            updated_at=home.updated_at
        )
    )


@router.delete("/{home_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_home_workspace(
    home_ctx: HomeContext = Depends(require_home_permission("home:delete")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(HomeModel).where(
        HomeModel.id == home_ctx.home_id,
        HomeModel.deleted_at.is_(None)
    )
    result = await db.execute(query)
    home = result.scalar_one_or_none()

    if not home:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    home.deleted_at = datetime.now(timezone.utc)
    home.status = "SUSPENDED"
    home.home_qr_status = "REVOKED"
    home.home_qr_revoked_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        entity_type="HOME",
        entity_id=home.id,
        action="HOME_DELETED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"name": home.name})
    )
    db.add(audit)
    await db.commit()

    try:
        await redis_client.delete(f"home:{home_ctx.home_id}:settings")
        await redis_client.delete(f"user:{home_ctx.user.id}:homes")
    except Exception:
        pass

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Home workspace '{home.name}' has been archived and deleted.")
    )
