from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    InventoryItemModel,
    ShoppingListModel,
    ShoppingListItemModel,
    UserModel,
    UserProfileModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.common import ApiSuccessResponse, MessageResponse
from src.schemas.shopping import (
    CheckItemRequest,
    ConvertFromInventoryRequest,
    CreateShoppingItemRequest,
    CreateShoppingListRequest,
    ShoppingListDTO,
    ShoppingListItemDTO,
    UpdateShoppingItemRequest
)

router = APIRouter(prefix="/homes/{home_id}/shopping", tags=["Shopping Lists"])


def to_shopping_item_dto(item: ShoppingListItemModel, assigned_name: Optional[str] = None) -> ShoppingListItemDTO:
    now = datetime.now(timezone.utc)
    return ShoppingListItemDTO(
        id=item.id or uuid4(),
        list_id=item.list_id or uuid4(),
        home_id=item.home_id or uuid4(),
        inventory_item_id=item.inventory_item_id,
        name=item.name or "Item",
        quantity=item.quantity if item.quantity is not None else Decimal("1.0"),
        unit=item.unit or "pcs",
        priority=item.priority or "MEDIUM",
        is_checked=bool(item.is_checked),
        added_by=getattr(item, "added_by", None),
        assigned_to=item.assigned_to,
        assigned_to_name=assigned_name,
        version=item.version or 1,
        created_at=item.created_at or now,
        updated_at=item.updated_at or now
    )


# ==================================
# Lists Management
# ==================================

@router.get("/lists", response_model=ApiSuccessResponse[List[ShoppingListDTO]])
async def list_shopping_lists(
    home_ctx: HomeContext = Depends(require_home_permission("shopping:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            ShoppingListModel,
            func.count(ShoppingListItemModel.id).label("total_items"),
            func.count(ShoppingListItemModel.id).filter(ShoppingListItemModel.is_checked == True).label("checked_items")
        )
        .outerjoin(ShoppingListItemModel, ShoppingListModel.id == ShoppingListItemModel.list_id)
        .where(ShoppingListModel.home_id == home_ctx.home_id)
        .group_by(ShoppingListModel.id)
        .order_by(ShoppingListModel.created_at.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    # If no list exists yet, auto-create "Main Shopping List"
    if not rows:
        default_list = ShoppingListModel(home_id=home_ctx.home_id, name="Main Shopping List")
        db.add(default_list)
        await db.commit()
        return ApiSuccessResponse(
            data=[
                ShoppingListDTO(
                    id=default_list.id,
                    home_id=default_list.home_id,
                    name=default_list.name,
                    total_items=0,
                    checked_items=0,
                    created_at=default_list.created_at,
                    updated_at=default_list.updated_at
                )
            ]
        )

    dtos = [
        ShoppingListDTO(
            id=lst.id,
            home_id=lst.home_id,
            name=lst.name,
            total_items=total,
            checked_items=checked,
            created_at=lst.created_at,
            updated_at=lst.updated_at
        )
        for lst, total, checked in rows
    ]

    return ApiSuccessResponse(data=dtos)


@router.post("/lists", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[ShoppingListDTO])
async def create_shopping_list(
    payload: CreateShoppingListRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:create")),
    db: AsyncSession = Depends(get_db),
):
    new_list = ShoppingListModel(home_id=home_ctx.home_id, name=payload.name.strip())
    db.add(new_list)
    await db.commit()

    return ApiSuccessResponse(
        data=ShoppingListDTO(
            id=new_list.id,
            home_id=new_list.home_id,
            name=new_list.name,
            total_items=0,
            checked_items=0,
            created_at=new_list.created_at,
            updated_at=new_list.updated_at
        )
    )


# ==================================
# List Items Management
# ==================================

@router.get("/lists/{list_id}/items", response_model=ApiSuccessResponse[List[ShoppingListItemDTO]])
async def list_items_for_shopping_list(
    list_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ShoppingListItemModel, UserProfileModel.display_name)
        .outerjoin(UserProfileModel, ShoppingListItemModel.assigned_to == UserProfileModel.user_id)
        .where(
            ShoppingListItemModel.list_id == list_id,
            ShoppingListItemModel.home_id == home_ctx.home_id
        )
        .order_by(ShoppingListItemModel.is_checked.asc(), ShoppingListItemModel.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    dtos = [
        to_shopping_item_dto(item, assigned_name)
        for item, assigned_name in rows
    ]

    return ApiSuccessResponse(data=dtos)


@router.post("/lists/{list_id}/items", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[ShoppingListItemDTO])
async def add_shopping_item(
    list_id: UUID,
    payload: CreateShoppingItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:create")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    new_item = ShoppingListItemModel(
        list_id=list_id,
        home_id=home_ctx.home_id,
        inventory_item_id=payload.inventory_item_id,
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        priority=payload.priority,
        is_checked=False,
        assigned_to=payload.assigned_to,
        version=1
    )
    db.add(new_item)
    await db.commit()

    # Broadcast concurrent live update event
    try:
        await redis_client.publish(
            f"home:{home_ctx.home_id}:shopping",
            f'{{"event":"ITEM_ADDED","item_id":"{new_item.id}","name":"{new_item.name}"}}'
        )
    except Exception:
        pass

    return ApiSuccessResponse(
        data=to_shopping_item_dto(new_item)
    )


@router.patch("/items/{item_id}/check", response_model=ApiSuccessResponse[ShoppingListItemDTO])
async def toggle_item_checked(
    item_id: UUID,
    payload: CheckItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:check")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(ShoppingListItemModel).where(
        ShoppingListItemModel.id == item_id,
        ShoppingListItemModel.home_id == home_ctx.home_id
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Shopping item not found.")

    # Optimistic concurrency check (if client provided version)
    if payload.version is not None and payload.version != item.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: This shopping item was modified by another family member. Please refresh."
        )

    item.is_checked = payload.is_checked
    item.version += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Broadcast live sync event to other family devices
    try:
        await redis_client.publish(
            f"home:{home_ctx.home_id}:shopping",
            f'{{"event":"ITEM_CHECKED","item_id":"{item.id}","is_checked":{str(item.is_checked).lower()},"version":{item.version}}}'
        )
    except Exception:
        pass

    return ApiSuccessResponse(
        data=to_shopping_item_dto(item)
    )


@router.patch("/items/{item_id}", response_model=ApiSuccessResponse[ShoppingListItemDTO])
async def update_shopping_item(
    item_id: UUID,
    payload: UpdateShoppingItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:edit")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(ShoppingListItemModel).where(
        ShoppingListItemModel.id == item_id,
        ShoppingListItemModel.home_id == home_ctx.home_id
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Shopping item not found.")

    if payload.version is not None and payload.version != item.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: This shopping item was modified concurrently."
        )

    if payload.name is not None:
        item.name = payload.name
    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.priority is not None:
        item.priority = payload.priority
    if payload.assigned_to is not None:
        item.assigned_to = payload.assigned_to
    if payload.is_checked is not None:
        item.is_checked = payload.is_checked

    item.version += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=to_shopping_item_dto(item)
    )


@router.delete("/items/{item_id}", response_model=ApiSuccessResponse[MessageResponse])
async def remove_shopping_item(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:delete")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    query = select(ShoppingListItemModel).where(
        ShoppingListItemModel.id == item_id,
        ShoppingListItemModel.home_id == home_ctx.home_id
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Shopping item not found.")

    await db.delete(item)
    await db.commit()

    try:
        await redis_client.publish(
            f"home:{home_ctx.home_id}:shopping",
            f'{{"event":"ITEM_DELETED","item_id":"{item_id}"}}'
        )
    except Exception:
        pass

    return ApiSuccessResponse(data=MessageResponse(message="Shopping item removed."))


# ==================================
# Convert Low-Stock Inventory
# ==================================

@router.post("/convert-from-inventory/{inventory_item_id}", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[ShoppingListItemDTO])
async def convert_low_stock_to_shopping_item(
    inventory_item_id: UUID,
    payload: ConvertFromInventoryRequest = ConvertFromInventoryRequest(),
    home_ctx: HomeContext = Depends(require_home_permission("shopping:create")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    # 1. Fetch inventory item
    inv_query = select(InventoryItemModel).where(
        InventoryItemModel.id == inventory_item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    inv_res = await db.execute(inv_query)
    inv_item = inv_res.scalar_one_or_none()

    if not inv_item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    # 2. Identify target shopping list
    target_list_id = payload.target_list_id
    if not target_list_id:
        list_query = select(ShoppingListModel).where(ShoppingListModel.home_id == home_ctx.home_id).limit(1)
        target_list = (await db.execute(list_query)).scalar_one_or_none()
        if not target_list:
            target_list = ShoppingListModel(home_id=home_ctx.home_id, name="Main Shopping List")
            db.add(target_list)
            await db.flush()
        target_list_id = target_list.id

    # 3. Calculate quantity
    qty = payload.quantity
    if not qty:
        if inv_item.min_threshold and inv_item.min_threshold > inv_item.quantity:
            qty = (inv_item.min_threshold * Decimal("2")) - inv_item.quantity
        else:
            qty = Decimal("1.0")

    # 4. Create shopping item
    shopping_item = ShoppingListItemModel(
        list_id=target_list_id,
        home_id=home_ctx.home_id,
        inventory_item_id=inv_item.id,
        name=inv_item.name,
        quantity=qty,
        unit=inv_item.unit,
        priority="HIGH" if inv_item.status in ["LOW_STOCK", "OUT_OF_STOCK"] else "MEDIUM",
        is_checked=False,
        version=1
    )
    db.add(shopping_item)
    await db.commit()

    return ApiSuccessResponse(
        data=to_shopping_item_dto(shopping_item)
    )
