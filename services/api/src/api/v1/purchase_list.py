from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    InventoryItemModel,
    PurchaseItemModel,
    PurchaseHistoryModel,
    StockMovementModel,
    UserProfileModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.common import ApiSuccessResponse, MessageResponse
from src.schemas.purchase_list import (
    PurchaseItemDTO,
    CreatePurchaseItemRequest,
    UpdatePurchaseItemRequest,
    PurchaseActionRequest,
    PurchaseHistoryDTO,
    PurchaseSummaryDTO
)

router = APIRouter(prefix="/homes/{home_id}", tags=["Home Purchase List"])


# ==============================================================================
# Active Purchase List
# ==============================================================================

@router.get("/purchase-list", response_model=ApiSuccessResponse[List[PurchaseItemDTO]])
async def get_home_purchase_list(
    home_ctx: HomeContext = Depends(require_home_permission("shopping:view")),
    status_filter: str = Query("PENDING", description="Filter by status: PENDING, PURCHASED, CANCELLED, ALL"),
    search: Optional[str] = Query(None, description="Search item name"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the shared Home Purchase List.
    """
    query = (
        select(
            PurchaseItemModel,
            UserProfileModel.display_name.label("added_by_name")
        )
        .outerjoin(UserProfileModel, PurchaseItemModel.added_by == UserProfileModel.user_id)
        .where(
            PurchaseItemModel.home_id == home_ctx.home_id,
            PurchaseItemModel.deleted_at == None
        )
    )

    if status_filter.upper() != "ALL":
        query = query.where(PurchaseItemModel.status == status_filter.upper())
    if search:
        query = query.where(PurchaseItemModel.name.ilike(f"%{search.strip()}%"))

    query = query.order_by(
        PurchaseItemModel.status.asc(),
        PurchaseItemModel.created_at.desc()
    )

    result = await db.execute(query)
    rows = result.all()

    dtos = [
        PurchaseItemDTO(
            id=item.id,
            home_id=item.home_id,
            inventory_item_id=item.inventory_item_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            notes=item.notes,
            status=item.status,
            added_by=item.added_by,
            added_by_name=added_name,
            purchased_by=item.purchased_by,
            purchased_by_name=None,
            purchased_at=item.purchased_at,
            restocked_to_inventory=item.restocked_to_inventory,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        for item, added_name in rows
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("/purchase-list", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[PurchaseItemDTO])
async def add_item_to_purchase_list(
    payload: CreatePurchaseItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:create")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Quickly add an item to the shared Home Purchase List.
    """
    # Verify optional inventory item exists in this Home
    if payload.inventory_item_id:
        inv_query = select(InventoryItemModel).where(
            InventoryItemModel.id == payload.inventory_item_id,
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at == None
        )
        inv = (await db.execute(inv_query)).scalar_one_or_none()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Linked inventory item not found in this Home."
            )

    new_item = PurchaseItemModel(
        home_id=home_ctx.home_id,
        inventory_item_id=payload.inventory_item_id,
        name=payload.name.strip(),
        quantity=payload.quantity,
        unit=payload.unit.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        status="PENDING",
        added_by=home_ctx.user.id,
        version=1
    )
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    try:
        await redis_client.publish(
            f"home:{home_ctx.home_id}:purchase_list",
            f'{{"event":"ITEM_ADDED","item_id":"{new_item.id}","name":"{new_item.name}"}}'
        )
    except Exception:
        pass

    return ApiSuccessResponse(
        data=PurchaseItemDTO(
            id=new_item.id,
            home_id=new_item.home_id,
            inventory_item_id=new_item.inventory_item_id,
            name=new_item.name,
            quantity=new_item.quantity,
            unit=new_item.unit,
            notes=new_item.notes,
            status=new_item.status,
            added_by=new_item.added_by,
            added_by_name=None,
            purchased_by=None,
            purchased_by_name=None,
            purchased_at=None,
            restocked_to_inventory=False,
            version=new_item.version,
            created_at=new_item.created_at,
            updated_at=new_item.updated_at
        )
    )


@router.patch("/purchase-list/{item_id}", response_model=ApiSuccessResponse[PurchaseItemDTO])
async def update_purchase_item(
    item_id: UUID,
    payload: UpdatePurchaseItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update details of a pending purchase item.
    """
    query = select(PurchaseItemModel).where(
        PurchaseItemModel.id == item_id,
        PurchaseItemModel.home_id == home_ctx.home_id,
        PurchaseItemModel.deleted_at == None
    )
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase item not found.")

    if payload.version is not None and payload.version != item.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: This purchase item was modified by another family member. Please refresh."
        )

    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.unit is not None:
        item.unit = payload.unit.strip()
    if payload.notes is not None:
        item.notes = payload.notes.strip() if payload.notes else None

    item.version += 1
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)

    return ApiSuccessResponse(
        data=PurchaseItemDTO(
            id=item.id,
            home_id=item.home_id,
            inventory_item_id=item.inventory_item_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            notes=item.notes,
            status=item.status,
            added_by=item.added_by,
            purchased_by=item.purchased_by,
            purchased_at=item.purchased_at,
            restocked_to_inventory=item.restocked_to_inventory,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    )


@router.delete("/purchase-list/{item_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_purchase_item(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel and remove an item from the active Purchase List.
    """
    query = select(PurchaseItemModel).where(
        PurchaseItemModel.id == item_id,
        PurchaseItemModel.home_id == home_ctx.home_id,
        PurchaseItemModel.deleted_at == None
    )
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase item not found.")

    item.status = "CANCELLED"
    item.deleted_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Purchase item removed."))


# ==============================================================================
# Purchase Execution & Inventory Restock Integration
# ==============================================================================

@router.post("/purchase-list/{item_id}/purchase", response_model=ApiSuccessResponse[PurchaseItemDTO])
async def mark_item_as_purchased(
    item_id: UUID,
    payload: PurchaseActionRequest,
    home_ctx: HomeContext = Depends(require_home_permission("shopping:check")),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Mark an item as PURCHASED.
    Moves item to Purchase History and optionally updates Home Inventory stock.
    """
    query = select(PurchaseItemModel).where(
        PurchaseItemModel.id == item_id,
        PurchaseItemModel.home_id == home_ctx.home_id,
        PurchaseItemModel.deleted_at == None
    )
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase item not found.")

    if item.status == "PURCHASED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item has already been purchased."
        )

    purchased_qty = payload.purchased_quantity or item.quantity
    now = datetime.now(timezone.utc)
    stock_mov_id = None
    restocked = False

    # Check inventory restock condition
    if payload.restock_inventory and item.inventory_item_id:
        inv_query = select(InventoryItemModel).where(
            InventoryItemModel.id == item.inventory_item_id,
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at == None
        )
        inv_item = (await db.execute(inv_query)).scalar_one_or_none()
        if inv_item:
            prev_qty = inv_item.quantity
            new_qty = prev_qty + purchased_qty
            inv_item.quantity = new_qty
            inv_item.status = "GOOD" if new_qty > (inv_item.min_threshold or Decimal("0")) else ("LOW" if new_qty > 0 else "OUT_OF_STOCK")
            inv_item.updated_at = now

            stock_movement = StockMovementModel(
                home_id=home_ctx.home_id,
                item_id=inv_item.id,
                movement_type="PURCHASE",
                quantity_delta=purchased_qty,
                previous_quantity=prev_qty,
                resulting_quantity=new_qty,
                reason=f"Restocked via Home Purchase List: {payload.notes or 'Bought in store'}",
                performed_by=home_ctx.user.id
            )
            db.add(stock_movement)
            await db.flush()
            stock_mov_id = stock_movement.id
            restocked = True

    # Update purchase item state
    item.status = "PURCHASED"
    item.purchased_by = home_ctx.user.id
    item.purchased_at = now
    item.restocked_to_inventory = restocked
    item.version += 1
    item.updated_at = now

    # Append to immutable purchase history ledger
    history_entry = PurchaseHistoryModel(
        home_id=home_ctx.home_id,
        purchase_item_id=item.id,
        inventory_item_id=item.inventory_item_id,
        stock_movement_id=stock_mov_id,
        name=item.name,
        quantity=purchased_qty,
        unit=item.unit,
        purchased_by=home_ctx.user.id,
        purchased_at=now,
        restocked_to_inventory=restocked,
        notes=payload.notes or item.notes
    )
    db.add(history_entry)
    await db.commit()
    await db.refresh(item)

    try:
        await redis_client.publish(
            f"home:{home_ctx.home_id}:purchase_list",
            f'{{"event":"ITEM_PURCHASED","item_id":"{item.id}","name":"{item.name}","restocked":{str(restocked).lower()}}}'
        )
    except Exception:
        pass

    return ApiSuccessResponse(
        data=PurchaseItemDTO(
            id=item.id,
            home_id=item.home_id,
            inventory_item_id=item.inventory_item_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            notes=item.notes,
            status=item.status,
            added_by=item.added_by,
            purchased_by=item.purchased_by,
            purchased_at=item.purchased_at,
            restocked_to_inventory=item.restocked_to_inventory,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    )


# ==============================================================================
# Purchase History & Suggestions
# ==============================================================================

@router.get("/purchase-history", response_model=ApiSuccessResponse[List[PurchaseHistoryDTO]])
async def get_purchase_history(
    home_ctx: HomeContext = Depends(require_home_permission("shopping:view")),
    search: Optional[str] = Query(None, description="Search past purchase"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Searchable historical ledger of all past completed purchases.
    """
    query = (
        select(
            PurchaseHistoryModel,
            UserProfileModel.display_name.label("purchased_by_name")
        )
        .outerjoin(UserProfileModel, PurchaseHistoryModel.purchased_by == UserProfileModel.user_id)
        .where(PurchaseHistoryModel.home_id == home_ctx.home_id)
    )

    if search:
        query = query.where(PurchaseHistoryModel.name.ilike(f"%{search.strip()}%"))

    query = (
        query
        .order_by(PurchaseHistoryModel.purchased_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    rows = result.all()

    dtos = [
        PurchaseHistoryDTO(
            id=hist.id,
            home_id=hist.home_id,
            purchase_item_id=hist.purchase_item_id,
            inventory_item_id=hist.inventory_item_id,
            stock_movement_id=hist.stock_movement_id,
            name=hist.name,
            quantity=hist.quantity,
            unit=hist.unit,
            purchased_by=hist.purchased_by,
            purchased_by_name=purchaser_name,
            purchased_at=hist.purchased_at,
            restocked_to_inventory=hist.restocked_to_inventory,
            notes=hist.notes,
            created_at=hist.created_at
        )
        for hist, purchaser_name in rows
    ]
    return ApiSuccessResponse(data=dtos)


@router.get("/purchase-list/suggestions")
async def get_pantry_replenishment_suggestions(
    home_ctx: HomeContext = Depends(require_home_permission("shopping:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get gentle suggestions for pantry items running low, without auto-adding them to the list.
    """
    # Active items already on the purchase list
    active_inv_ids_subq = select(PurchaseItemModel.inventory_item_id).where(
        PurchaseItemModel.home_id == home_ctx.home_id,
        PurchaseItemModel.status == "PENDING",
        PurchaseItemModel.inventory_item_id != None,
        PurchaseItemModel.deleted_at == None
    )

    # Low stock or out of stock items
    query = select(InventoryItemModel).where(
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.item_type == "CONSUMABLE",
        InventoryItemModel.status.in_(["LOW", "OUT_OF_STOCK"]),
        InventoryItemModel.deleted_at == None,
        InventoryItemModel.id.not_in(active_inv_ids_subq)
    ).order_by(InventoryItemModel.name.asc())

    result = await db.execute(query)
    items = result.scalars().all()

    suggestions = []
    for item in items:
        if item.preferred_quantity and item.preferred_quantity > item.quantity:
            suggested_qty = item.preferred_quantity - item.quantity
        elif item.min_threshold and item.min_threshold > item.quantity:
            suggested_qty = (item.min_threshold * Decimal("2")) - item.quantity
        else:
            suggested_qty = item.min_threshold or Decimal("1.000")

        suggestions.append({
            "inventory_item_id": str(item.id),
            "name": item.name,
            "current_quantity": float(item.quantity),
            "suggested_quantity": float(suggested_qty),
            "unit": item.unit,
            "status": item.status,
            "location_path": item.location_path,
        })

    return ApiSuccessResponse(data=suggestions)
