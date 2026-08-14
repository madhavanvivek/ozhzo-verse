import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.core.locations import build_location_path_map
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AssetLoanModel,
    AuditLogModel,
    HomeMemberModel,
    InventoryCategoryModel,
    InventoryItemModel,
    LocationModel,
    LocationMovementModel,
    StockMovementModel,
    UserModel
)
from src.infrastructure.cache.redis_client import get_redis_client
from src.schemas.common import ApiSuccessResponse
from src.schemas.inventory import (
    AssetLoanDTO,
    BorrowItemRequest,
    CreateCategoryRequest,
    CreateInventoryItemRequest,
    InventoryCategoryDTO,
    InventoryItemDTO,
    InventorySummaryDTO,
    LocationMovementDTO,
    MessageResponse,
    MoveItemRequest,
    PaginatedInventoryResponse,
    ReturnItemRequest,
    StockMovementDTO,
    StockMovementRequest,
    UpdateCategoryRequest,
    UpdateInventoryItemRequest
)

router = APIRouter(prefix="/homes/{home_id}/inventory", tags=["Inventory & Assets"])


def calculate_stock_status(quantity: Decimal, min_threshold: Optional[Decimal]) -> str:
    if quantity <= Decimal("0"):
        return "OUT_OF_STOCK"
    if min_threshold is not None and quantity <= min_threshold:
        return "LOW"
    return "GOOD"


def calculate_expiry_status(expiry_date: Optional[date]) -> str:
    if not expiry_date:
        return "NORMAL"
    today = date.today()
    if expiry_date < today:
        return "EXPIRED"
    if expiry_date <= today + timedelta(days=7):
        return "EXPIRING_SOON"
    return "NORMAL"


# ==============================================================================
# Categories API
# ==============================================================================

@router.get("/categories", response_model=ApiSuccessResponse[List[InventoryCategoryDTO]])
async def list_categories(
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            InventoryCategoryModel,
            func.count(InventoryItemModel.id).label("item_count")
        )
        .outerjoin(
            InventoryItemModel,
            (InventoryCategoryModel.id == InventoryItemModel.category_id) & (InventoryItemModel.deleted_at == None)
        )
        .where(InventoryCategoryModel.home_id == home_ctx.home_id)
        .group_by(InventoryCategoryModel.id)
        .order_by(InventoryCategoryModel.sort_order.asc(), InventoryCategoryModel.name.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    dtos = [
        InventoryCategoryDTO(
            id=cat.id,
            home_id=cat.home_id,
            name=cat.name,
            icon=cat.icon,
            color=cat.color,
            sort_order=cat.sort_order,
            item_count=count,
            created_at=cat.created_at,
            updated_at=cat.updated_at
        )
        for cat, count in rows
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("/categories", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[InventoryCategoryDTO])
async def create_category(
    payload: CreateCategoryRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:create")),
    db: AsyncSession = Depends(get_db),
):
    dup_res = await db.execute(
        select(InventoryCategoryModel).where(
            InventoryCategoryModel.home_id == home_ctx.home_id,
            InventoryCategoryModel.name.ilike(payload.name.strip())
        )
    )
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{payload.name}' already exists in this Home."
        )

    new_cat = InventoryCategoryModel(
        home_id=home_ctx.home_id,
        name=payload.name.strip(),
        icon=payload.icon,
        color=payload.color,
        sort_order=payload.sort_order
    )
    db.add(new_cat)
    await db.commit()

    return ApiSuccessResponse(
        data=InventoryCategoryDTO(
            id=new_cat.id,
            home_id=new_cat.home_id,
            name=new_cat.name,
            icon=new_cat.icon,
            color=new_cat.color,
            sort_order=new_cat.sort_order,
            item_count=0,
            created_at=new_cat.created_at,
            updated_at=new_cat.updated_at
        )
    )


# ==============================================================================
# Items & Assets API
# ==============================================================================

@router.get("/items", response_model=ApiSuccessResponse[PaginatedInventoryResponse])
async def list_inventory_items(
    item_type: Optional[str] = Query(None, pattern="^(CONSUMABLE|ASSET)$"),
    category_id: Optional[UUID] = Query(None),
    location_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    asset_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("name", pattern="^(name|quantity|expiry_date|created_at)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    filters = [
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    ]

    if item_type:
        filters.append(InventoryItemModel.item_type == item_type)
    if category_id:
        filters.append(InventoryItemModel.category_id == category_id)
    if location_id:
        filters.append(InventoryItemModel.location_id == location_id)
    if status:
        filters.append(InventoryItemModel.status == status.upper())
    if asset_status:
        filters.append(InventoryItemModel.asset_status == asset_status.upper())
    if search:
        s = f"%{search.strip()}%"
        filters.append(
            or_(
                InventoryItemModel.name.ilike(s),
                InventoryItemModel.description.ilike(s),
                InventoryItemModel.location_path.ilike(s),
                InventoryItemModel.current_holder_name.ilike(s),
                InventoryItemModel.notes.ilike(s)
            )
        )

    count_query = select(func.count()).select_from(InventoryItemModel).where(*filters)
    total = (await db.execute(count_query)).scalar() or 0

    sort_col = getattr(InventoryItemModel, sort_by)
    sort_expr = sort_col.desc().nullslast() if order == "desc" else sort_col.asc().nullslast()

    query = (
        select(InventoryItemModel)
        .options(
            selectinload(InventoryItemModel.category),
            selectinload(InventoryItemModel.location)
        )
        .where(*filters)
        .order_by(sort_expr)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(query)).scalars().all()
    path_map = await build_location_path_map(db, home_ctx.home_id)

    item_dtos = [
        InventoryItemDTO(
            id=i.id,
            home_id=i.home_id,
            template_id=i.template_id,
            category_id=i.category_id,
            category_name=i.category.name if i.category else None,
            location_id=i.location_id,
            location_path=path_map.get(i.location_id) if i.location_id else None,
            item_type=i.item_type,
            name=i.name,
            description=i.description,
            quantity=i.quantity,
            unit=i.unit,
            min_threshold=i.min_threshold,
            preferred_quantity=i.preferred_quantity,
            max_quantity=i.max_quantity,
            condition=i.condition,
            asset_status=i.asset_status,
            current_holder_name=i.current_holder_name,
            current_holder_user_id=i.current_holder_user_id,
            last_seen_at=i.last_seen_at,
            last_seen_by=i.last_seen_by,
            last_seen_location_id=i.last_seen_location_id,
            expiry_date=i.expiry_date,
            status=i.status,
            expiry_status=i.expiry_status,
            notes=i.notes,
            created_by=i.created_by,
            created_at=i.created_at,
            updated_at=i.updated_at
        )
        for i in items
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return ApiSuccessResponse(
        data=PaginatedInventoryResponse(
            items=item_dtos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.post("/items", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[InventoryItemDTO])
async def create_inventory_item(
    payload: CreateInventoryItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:create")),
    db: AsyncSession = Depends(get_db),
):
    # Validate location belongs to same home
    loc_path = None
    if payload.location_id:
        loc_res = await db.execute(
            select(LocationModel).where(
                LocationModel.id == payload.location_id,
                LocationModel.home_id == home_ctx.home_id,
                LocationModel.deleted_at == None
            )
        )
        if not loc_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Location not found or belongs to another Home.")
        path_map = await build_location_path_map(db, home_ctx.home_id)
        loc_path = path_map.get(payload.location_id)

    computed_status = calculate_stock_status(payload.quantity, payload.min_threshold)
    computed_expiry = calculate_expiry_status(payload.expiry_date)

    now = datetime.now(timezone.utc)
    new_item = InventoryItemModel(
        home_id=home_ctx.home_id,
        template_id=payload.template_id,
        category_id=payload.category_id,
        location_id=payload.location_id,
        location_path=loc_path,
        item_type=payload.item_type,
        name=payload.name,
        description=payload.description,
        quantity=payload.quantity,
        unit=payload.unit,
        min_threshold=payload.min_threshold,
        preferred_quantity=payload.preferred_quantity,
        max_quantity=payload.max_quantity,
        condition=payload.condition,
        asset_status="AVAILABLE",
        last_seen_at=now,
        last_seen_by=home_ctx.user.id,
        last_seen_location_id=payload.location_id,
        expiry_date=payload.expiry_date,
        status=computed_status,
        expiry_status=computed_expiry,
        notes=payload.notes,
        created_by=home_ctx.user.id
    )
    db.add(new_item)
    await db.flush()

    # Initial stock movement for consumables
    if payload.item_type == "CONSUMABLE" and payload.quantity > 0:
        movement = StockMovementModel(
            home_id=home_ctx.home_id,
            item_id=new_item.id,
            movement_type="ADD",
            quantity_delta=payload.quantity,
            previous_quantity=Decimal("0.000"),
            resulting_quantity=payload.quantity,
            reason="Initial stock entry",
            performed_by=home_ctx.user.id
        )
        db.add(movement)

    # Initial location movement if location assigned
    if payload.location_id:
        loc_move = LocationMovementModel(
            home_id=home_ctx.home_id,
            item_id=new_item.id,
            from_location_id=None,
            to_location_id=payload.location_id,
            from_location_path=None,
            to_location_path=loc_path or "Home",
            reason="Initial placement",
            moved_by=home_ctx.user.id
        )
        db.add(loc_move)

    await db.commit()

    cat_name = None
    if new_item.category_id:
        cat = await db.get(InventoryCategoryModel, new_item.category_id)
        if cat:
            cat_name = cat.name

    return ApiSuccessResponse(
        data=InventoryItemDTO(
            id=new_item.id,
            home_id=new_item.home_id,
            template_id=new_item.template_id,
            category_id=new_item.category_id,
            category_name=cat_name,
            location_id=new_item.location_id,
            location_path=new_item.location_path,
            item_type=new_item.item_type,
            name=new_item.name,
            description=new_item.description,
            quantity=new_item.quantity,
            unit=new_item.unit,
            min_threshold=new_item.min_threshold,
            preferred_quantity=new_item.preferred_quantity,
            max_quantity=new_item.max_quantity,
            condition=new_item.condition,
            asset_status=new_item.asset_status,
            current_holder_name=new_item.current_holder_name,
            current_holder_user_id=new_item.current_holder_user_id,
            last_seen_at=new_item.last_seen_at,
            last_seen_by=new_item.last_seen_by,
            last_seen_location_id=new_item.last_seen_location_id,
            expiry_date=new_item.expiry_date,
            status=new_item.status,
            expiry_status=new_item.expiry_status,
            notes=new_item.notes,
            created_by=new_item.created_by,
            created_at=new_item.created_at,
            updated_at=new_item.updated_at
        )
    )


@router.get("/items/{item_id}", response_model=ApiSuccessResponse[InventoryItemDTO])
async def get_inventory_item(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(InventoryItemModel)
        .options(
            selectinload(InventoryItemModel.category),
            selectinload(InventoryItemModel.location)
        )
        .where(
            InventoryItemModel.id == item_id,
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at == None
        )
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    path_map = await build_location_path_map(db, home_ctx.home_id)

    return ApiSuccessResponse(
        data=InventoryItemDTO(
            id=item.id,
            home_id=item.home_id,
            template_id=item.template_id,
            category_id=item.category_id,
            category_name=item.category.name if item.category else None,
            location_id=item.location_id,
            location_path=path_map.get(item.location_id) if item.location_id else None,
            item_type=item.item_type,
            name=item.name,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            min_threshold=item.min_threshold,
            preferred_quantity=item.preferred_quantity,
            max_quantity=item.max_quantity,
            condition=item.condition,
            asset_status=item.asset_status,
            current_holder_name=item.current_holder_name,
            current_holder_user_id=item.current_holder_user_id,
            last_seen_at=item.last_seen_at,
            last_seen_by=item.last_seen_by,
            last_seen_location_id=item.last_seen_location_id,
            expiry_date=item.expiry_date,
            status=item.status,
            expiry_status=item.expiry_status,
            notes=item.notes,
            created_by=item.created_by,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    )


@router.patch("/items/{item_id}", response_model=ApiSuccessResponse[InventoryItemDTO])
async def update_inventory_item(
    item_id: UUID,
    payload: UpdateInventoryItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    if payload.template_id is not None:
        item.template_id = payload.template_id
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.category_id is not None:
        item.category_id = payload.category_id
    if payload.description is not None:
        item.description = payload.description
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.min_threshold is not None:
        item.min_threshold = payload.min_threshold
    if payload.preferred_quantity is not None:
        item.preferred_quantity = payload.preferred_quantity
    if payload.max_quantity is not None:
        item.max_quantity = payload.max_quantity
    if payload.condition is not None:
        item.condition = payload.condition
    if payload.expiry_date is not None:
        item.expiry_date = payload.expiry_date
    if payload.notes is not None:
        item.notes = payload.notes

    # If quantity is updated directly, create ADJUST movement
    if payload.quantity is not None and payload.quantity != item.quantity:
        delta = payload.quantity - item.quantity
        movement = StockMovementModel(
            home_id=home_ctx.home_id,
            item_id=item.id,
            movement_type="ADJUST",
            quantity_delta=delta,
            previous_quantity=item.quantity,
            resulting_quantity=payload.quantity,
            reason="Manual quantity adjustment",
            performed_by=home_ctx.user.id
        )
        db.add(movement)
        item.quantity = payload.quantity

    item.status = calculate_stock_status(item.quantity, item.min_threshold)
    item.expiry_status = calculate_expiry_status(item.expiry_date)
    item.updated_at = datetime.now(timezone.utc)

    await db.commit()
    path_map = await build_location_path_map(db, home_ctx.home_id)

    cat_name = None
    if item.category_id:
        cat = await db.get(InventoryCategoryModel, item.category_id)
        if cat:
            cat_name = cat.name

    return ApiSuccessResponse(
        data=InventoryItemDTO(
            id=item.id,
            home_id=item.home_id,
            template_id=item.template_id,
            category_id=item.category_id,
            category_name=cat_name,
            location_id=item.location_id,
            location_path=path_map.get(item.location_id) if item.location_id else None,
            item_type=item.item_type,
            name=item.name,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            min_threshold=item.min_threshold,
            preferred_quantity=item.preferred_quantity,
            max_quantity=item.max_quantity,
            condition=item.condition,
            asset_status=item.asset_status,
            current_holder_name=item.current_holder_name,
            current_holder_user_id=item.current_holder_user_id,
            last_seen_at=item.last_seen_at,
            last_seen_by=item.last_seen_by,
            last_seen_location_id=item.last_seen_location_id,
            expiry_date=item.expiry_date,
            status=item.status,
            expiry_status=item.expiry_status,
            notes=item.notes,
            created_by=item.created_by,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    )


@router.delete("/items/{item_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_inventory_item(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:delete")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    item.deleted_at = datetime.now(timezone.utc)
    item.asset_status = "ARCHIVED"
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Item '{item.name}' has been archived and deleted.")
    )


# ==============================================================================
# Physical Location Movements API
# ==============================================================================

@router.post("/items/{item_id}/move", response_model=ApiSuccessResponse[InventoryItemDTO])
async def move_inventory_item(
    item_id: UUID,
    payload: MoveItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    # Validate target location belongs to same home
    loc_query = select(LocationModel).where(
        LocationModel.id == payload.to_location_id,
        LocationModel.home_id == home_ctx.home_id,
        LocationModel.deleted_at == None
    )
    loc_res = await db.execute(loc_query)
    to_loc = loc_res.scalar_one_or_none()
    if not to_loc:
        raise HTTPException(status_code=400, detail="Target location not found or belongs to another Home.")

    path_map = await build_location_path_map(db, home_ctx.home_id)
    from_path = path_map.get(item.location_id) if item.location_id else "Unassigned"
    to_path = path_map.get(payload.to_location_id, to_loc.name)

    now = datetime.now(timezone.utc)

    # Log relocation
    movement = LocationMovementModel(
        home_id=home_ctx.home_id,
        item_id=item.id,
        from_location_id=item.location_id,
        to_location_id=payload.to_location_id,
        from_location_path=from_path,
        to_location_path=to_path,
        reason=payload.reason,
        moved_by=home_ctx.user.id,
        moved_at=now
    )
    db.add(movement)

    # Update item
    item.location_id = payload.to_location_id
    item.location_path = to_path
    item.last_seen_at = now
    item.last_seen_by = home_ctx.user.id
    item.last_seen_location_id = payload.to_location_id
    item.updated_at = now

    await db.commit()

    cat_name = None
    if item.category_id:
        cat = await db.get(InventoryCategoryModel, item.category_id)
        if cat:
            cat_name = cat.name

    return ApiSuccessResponse(
        data=InventoryItemDTO(
            id=item.id,
            home_id=item.home_id,
            category_id=item.category_id,
            category_name=cat_name,
            location_id=item.location_id,
            location_path=item.location_path,
            item_type=item.item_type,
            name=item.name,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            min_threshold=item.min_threshold,
            preferred_quantity=item.preferred_quantity,
            max_quantity=item.max_quantity,
            condition=item.condition,
            asset_status=item.asset_status,
            current_holder_name=item.current_holder_name,
            current_holder_user_id=item.current_holder_user_id,
            last_seen_at=item.last_seen_at,
            last_seen_by=item.last_seen_by,
            last_seen_location_id=item.last_seen_location_id,
            expiry_date=item.expiry_date,
            status=item.status,
            expiry_status=item.expiry_status,
            notes=item.notes,
            created_by=item.created_by,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    )


@router.get("/items/{item_id}/location-history", response_model=ApiSuccessResponse[List[LocationMovementDTO]])
async def get_item_location_history(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(LocationMovementModel)
        .where(
            LocationMovementModel.item_id == item_id,
            LocationMovementModel.home_id == home_ctx.home_id
        )
        .order_by(LocationMovementModel.moved_at.desc())
    )
    result = await db.execute(query)
    movements = result.scalars().all()

    return ApiSuccessResponse(
        data=[
            LocationMovementDTO(
                id=m.id,
                home_id=m.home_id,
                item_id=m.item_id,
                from_location_id=m.from_location_id,
                to_location_id=m.to_location_id,
                from_location_path=m.from_location_path,
                to_location_path=m.to_location_path,
                reason=m.reason,
                moved_by=m.moved_by,
                moved_at=m.moved_at
            )
            for m in movements
        ]
    )


# ==============================================================================
# Asset Lending / Borrowing API
# ==============================================================================

@router.post("/items/{item_id}/borrow", response_model=ApiSuccessResponse[AssetLoanDTO])
async def borrow_asset(
    item_id: UUID,
    payload: BorrowItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Asset not found.")

    if item.asset_status == "BORROWED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset is already borrowed by {item.current_holder_name}."
        )

    now = datetime.now(timezone.utc)
    new_loan = AssetLoanModel(
        home_id=home_ctx.home_id,
        item_id=item.id,
        borrower_type=payload.borrower_type,
        borrower_user_id=payload.borrower_user_id,
        borrower_name=payload.borrower_name.strip(),
        borrower_contact=payload.borrower_contact,
        loan_status="ACTIVE",
        borrowed_at=now,
        expected_return_at=payload.expected_return_at,
        issued_by=home_ctx.user.id,
        notes=payload.notes
    )
    db.add(new_loan)

    # Update item status
    item.asset_status = "BORROWED"
    item.current_holder_name = payload.borrower_name.strip()
    item.current_holder_user_id = payload.borrower_user_id
    item.updated_at = now

    await db.commit()

    return ApiSuccessResponse(
        data=AssetLoanDTO(
            id=new_loan.id,
            home_id=new_loan.home_id,
            item_id=new_loan.item_id,
            item_name=item.name,
            borrower_type=new_loan.borrower_type,
            borrower_user_id=new_loan.borrower_user_id,
            borrower_name=new_loan.borrower_name,
            borrower_contact=new_loan.borrower_contact,
            loan_status=new_loan.loan_status,
            borrowed_at=new_loan.borrowed_at,
            expected_return_at=new_loan.expected_return_at,
            returned_at=new_loan.returned_at,
            return_location_id=new_loan.return_location_id,
            return_location_path=new_loan.return_location_path,
            issued_by=new_loan.issued_by,
            received_by=new_loan.received_by,
            notes=new_loan.notes,
            created_at=new_loan.created_at,
            updated_at=new_loan.updated_at
        )
    )


@router.post("/items/{item_id}/return", response_model=ApiSuccessResponse[AssetLoanDTO])
async def return_asset(
    item_id: UUID,
    payload: ReturnItemRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Asset not found.")

    if item.asset_status != "BORROWED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset is not currently recorded as borrowed."
        )

    # Find active loan
    loan_query = select(AssetLoanModel).where(
        AssetLoanModel.item_id == item.id,
        AssetLoanModel.home_id == home_ctx.home_id,
        AssetLoanModel.loan_status == "ACTIVE"
    ).order_by(AssetLoanModel.borrowed_at.desc())
    loan_res = await db.execute(loan_query)
    active_loan = loan_res.scalars().first()

    if not active_loan:
        raise HTTPException(status_code=400, detail="No active loan record found for this asset.")

    now = datetime.now(timezone.utc)
    path_map = await build_location_path_map(db, home_ctx.home_id)

    return_loc_id = payload.return_location_id or item.location_id
    return_loc_path = path_map.get(return_loc_id) if return_loc_id else item.location_path

    active_loan.loan_status = "RETURNED"
    active_loan.returned_at = now
    active_loan.return_location_id = return_loc_id
    active_loan.return_location_path = return_loc_path
    active_loan.received_by = home_ctx.user.id
    if payload.notes:
        active_loan.notes = f"{active_loan.notes or ''} | Return notes: {payload.notes}".strip()
    active_loan.updated_at = now

    # Reset asset status
    item.asset_status = "AVAILABLE"
    item.current_holder_name = None
    item.current_holder_user_id = None
    if payload.return_location_id:
        item.location_id = payload.return_location_id
        item.location_path = return_loc_path
    item.last_seen_at = now
    item.last_seen_by = home_ctx.user.id
    item.last_seen_location_id = return_loc_id
    item.updated_at = now

    await db.commit()

    return ApiSuccessResponse(
        data=AssetLoanDTO(
            id=active_loan.id,
            home_id=active_loan.home_id,
            item_id=active_loan.item_id,
            item_name=item.name,
            borrower_type=active_loan.borrower_type,
            borrower_user_id=active_loan.borrower_user_id,
            borrower_name=active_loan.borrower_name,
            borrower_contact=active_loan.borrower_contact,
            loan_status=active_loan.loan_status,
            borrowed_at=active_loan.borrowed_at,
            expected_return_at=active_loan.expected_return_at,
            returned_at=active_loan.returned_at,
            return_location_id=active_loan.return_location_id,
            return_location_path=active_loan.return_location_path,
            issued_by=active_loan.issued_by,
            received_by=active_loan.received_by,
            notes=active_loan.notes,
            created_at=active_loan.created_at,
            updated_at=active_loan.updated_at
        )
    )


@router.get("/items/{item_id}/loans", response_model=ApiSuccessResponse[List[AssetLoanDTO]])
async def get_item_loan_history(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AssetLoanModel)
        .where(
            AssetLoanModel.item_id == item_id,
            AssetLoanModel.home_id == home_ctx.home_id
        )
        .order_by(AssetLoanModel.borrowed_at.desc())
    )
    result = await db.execute(query)
    loans = result.scalars().all()

    return ApiSuccessResponse(
        data=[
            AssetLoanDTO(
                id=l.id,
                home_id=l.home_id,
                item_id=l.item_id,
                borrower_type=l.borrower_type,
                borrower_user_id=l.borrower_user_id,
                borrower_name=l.borrower_name,
                borrower_contact=l.borrower_contact,
                loan_status=l.loan_status,
                borrowed_at=l.borrowed_at,
                expected_return_at=l.expected_return_at,
                returned_at=l.returned_at,
                return_location_id=l.return_location_id,
                return_location_path=l.return_location_path,
                issued_by=l.issued_by,
                received_by=l.received_by,
                notes=l.notes,
                created_at=l.created_at,
                updated_at=l.updated_at
            )
            for l in loans
        ]
    )


@router.get("/loans", response_model=ApiSuccessResponse[List[AssetLoanDTO]])
async def list_home_active_loans(
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AssetLoanModel, InventoryItemModel.name)
        .join(InventoryItemModel, AssetLoanModel.item_id == InventoryItemModel.id)
        .where(
            AssetLoanModel.home_id == home_ctx.home_id,
            AssetLoanModel.loan_status.in_(["ACTIVE", "OVERDUE"])
        )
        .order_by(AssetLoanModel.borrowed_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return ApiSuccessResponse(
        data=[
            AssetLoanDTO(
                id=l.id,
                home_id=l.home_id,
                item_id=l.item_id,
                item_name=item_name,
                borrower_type=l.borrower_type,
                borrower_user_id=l.borrower_user_id,
                borrower_name=l.borrower_name,
                borrower_contact=l.borrower_contact,
                loan_status=l.loan_status,
                borrowed_at=l.borrowed_at,
                expected_return_at=l.expected_return_at,
                returned_at=l.returned_at,
                return_location_id=l.return_location_id,
                return_location_path=l.return_location_path,
                issued_by=l.issued_by,
                received_by=l.received_by,
                notes=l.notes,
                created_at=l.created_at,
                updated_at=l.updated_at
            )
            for l, item_name in rows
        ]
    )


# ==============================================================================
# Stock Movements (Quantity Ledger) API
# ==============================================================================

@router.post("/items/{item_id}/movements", response_model=ApiSuccessResponse[StockMovementDTO])
async def record_stock_movement(
    item_id: UUID,
    payload: StockMovementRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    prev_qty = item.quantity

    if payload.movement_type in ["ADD", "PURCHASE", "RETURN"]:
        delta = payload.quantity
        new_qty = prev_qty + delta
    elif payload.movement_type in ["CONSUME", "WASTE"]:
        delta = -payload.quantity
        new_qty = max(Decimal("0.000"), prev_qty - payload.quantity)
    elif payload.movement_type == "ADJUST":
        delta = payload.quantity - prev_qty
        new_qty = payload.quantity
    else:
        raise HTTPException(status_code=400, detail="Invalid movement type.")

    now = datetime.now(timezone.utc)
    movement = StockMovementModel(
        home_id=home_ctx.home_id,
        item_id=item.id,
        movement_type=payload.movement_type,
        quantity_delta=delta,
        previous_quantity=prev_qty,
        resulting_quantity=new_qty,
        reason=payload.reason,
        performed_by=home_ctx.user.id,
        created_at=now
    )
    db.add(movement)

    item.quantity = new_qty
    item.status = calculate_stock_status(new_qty, item.min_threshold)
    item.updated_at = now

    await db.commit()

    return ApiSuccessResponse(
        data=StockMovementDTO(
            id=movement.id,
            home_id=movement.home_id,
            item_id=movement.item_id,
            movement_type=movement.movement_type,
            quantity_delta=movement.quantity_delta,
            previous_quantity=movement.previous_quantity,
            resulting_quantity=movement.resulting_quantity,
            reason=movement.reason,
            performed_by=movement.performed_by,
            created_at=movement.created_at
        )
    )


@router.get("/items/{item_id}/movements", response_model=ApiSuccessResponse[List[StockMovementDTO]])
async def get_item_stock_movements(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(StockMovementModel)
        .where(
            StockMovementModel.item_id == item_id,
            StockMovementModel.home_id == home_ctx.home_id
        )
        .order_by(StockMovementModel.created_at.desc())
    )
    result = await db.execute(query)
    movements = result.scalars().all()

    return ApiSuccessResponse(
        data=[
            StockMovementDTO(
                id=m.id,
                home_id=m.home_id,
                item_id=m.item_id,
                movement_type=m.movement_type,
                quantity_delta=m.quantity_delta,
                previous_quantity=m.previous_quantity,
                resulting_quantity=m.resulting_quantity,
                reason=m.reason,
                performed_by=m.performed_by,
                created_at=m.created_at
            )
            for m in movements
        ]
    )


# ==============================================================================
# Summary API
# ==============================================================================

@router.get("/summary", response_model=ApiSuccessResponse[InventorySummaryDTO])
async def get_inventory_summary(
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItemModel).where(
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    items = (await db.execute(query)).scalars().all()

    total = len(items)
    consumables = len([i for i in items if i.item_type == "CONSUMABLE"])
    assets = len([i for i in items if i.item_type == "ASSET"])
    good = len([i for i in items if i.status == "GOOD"])
    low = len([i for i in items if i.status == "LOW"])
    out = len([i for i in items if i.status == "OUT_OF_STOCK"])
    expired = len([i for i in items if i.expiry_status == "EXPIRED"])
    expiring_soon = len([i for i in items if i.expiry_status == "EXPIRING_SOON"])
    borrowed = len([i for i in items if i.asset_status == "BORROWED"])

    return ApiSuccessResponse(
        data=InventorySummaryDTO(
            total_items=total,
            consumables_count=consumables,
            assets_count=assets,
            good_stock_count=good,
            low_stock_count=low,
            out_of_stock_count=out,
            expired_count=expired,
            expiring_soon_count=expiring_soon,
            borrowed_assets_count=borrowed
        )
    )
