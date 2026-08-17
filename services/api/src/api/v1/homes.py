import json
import uuid
from datetime import datetime, timezone
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AuditLogModel,
    HomeModel,
    HomeMemberModel,
    InventoryCategoryModel,
    InventoryItemModel,
    TaskModel,
    UserModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.core.exceptions import TierLimitExceededException
from src.schemas.common import ApiSuccessResponse
from src.schemas.home import CreateHomeRequest, HomeDTO, HomeDetailDTO, MessageResponse, UpdateHomeRequest

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
            HomeModel.deleted_at == None
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
    if current_user.phone_number and not current_user.mobile_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mobile number verification is required before creating a Home."
        )

    # Check free tier limit (1 active owned home for regular users)
    if not getattr(current_user, "is_super_admin", False):
        query = select(HomeModel).where(
            HomeModel.created_by == current_user.id,
            HomeModel.deleted_at == None
        )
        existing_result = await db.execute(query)
        existing_homes = existing_result.scalars().all()
        if len(existing_homes) >= 1:
            raise TierLimitExceededException(resource="homes", limit=1)

    # 1. Create Home record
    new_home = HomeModel(
        id=uuid.uuid4(),
        name=payload.name,
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
        details=json.dumps({"name": new_home.name, "country": new_home.country})
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


@router.get("/{home_id}", response_model=ApiSuccessResponse[HomeDetailDTO])
async def get_home_details(
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db)
):
    query = select(HomeModel).where(
        HomeModel.id == home_ctx.home_id,
        HomeModel.deleted_at == None
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
        InventoryItemModel.deleted_at == None
    )
    inventory_count = (await db.execute(inventory_count_query)).scalar() or 0

    chores_count_query = select(func.count()).select_from(TaskModel).where(
        TaskModel.home_id == home_ctx.home_id,
        TaskModel.status.in_(["TODO", "IN_PROGRESS"]),
        TaskModel.deleted_at == None
    )
    chores_count = (await db.execute(chores_count_query)).scalar() or 0

    return ApiSuccessResponse(
        data=HomeDetailDTO(
            id=home.id,
            name=home.name,
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
        HomeModel.deleted_at == None
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
        HomeModel.deleted_at == None
    )
    result = await db.execute(query)
    home = result.scalar_one_or_none()

    if not home:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    home.deleted_at = datetime.now(timezone.utc)
    home.status = "SUSPENDED"

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
