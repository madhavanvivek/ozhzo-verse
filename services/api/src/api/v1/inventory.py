from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
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
    ConsumeStockRequest,
    CreateCategoryRequest,
    CreateInventoryItemRequest,
    InventoryCategoryDTO,
    InventoryItemDTO,
    InventorySummaryDTO,
    LocationMovementDTO,
    MessageResponse,
    MoveItemRequest,
    PaginatedInventoryResponse,
    RestockStockRequest,
    ReturnItemRequest,
    StockMovementDTO,
    StockMovementRequest,
    UpdateCategoryRequest,
    UpdateInventoryItemRequest,
    QRLabelResponse
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


def calculate_warranty_status(warranty_expiry_date: Optional[date]) -> str:
    if not warranty_expiry_date:
        return "NO_WARRANTY"
    today = date.today()
    if warranty_expiry_date < today:
        return "EXPIRED"
    if warranty_expiry_date <= today + timedelta(days=30):
        return "EXPIRING_SOON"
    return "ACTIVE"


def to_inventory_item_dto(item: InventoryItemModel, path_map: Optional[dict] = None, cat_name: Optional[str] = None) -> InventoryItemDTO:
    loc_path = path_map.get(item.location_id) if (path_map and item.location_id) else item.location_path
    resolved_cat_name = cat_name or (item.category.name if getattr(item, "category", None) else None)
    now = datetime.now(timezone.utc)
    return InventoryItemDTO(
        id=item.id or uuid4(),
        home_id=item.home_id,
        template_id=item.template_id,
        category_id=item.category_id,
        category_name=resolved_cat_name,
        location_id=item.location_id,
        location_path=loc_path,
        item_type=item.item_type or "CONSUMABLE",
        name=item.name,
        description=item.description,
        quantity=item.quantity if item.quantity is not None else Decimal("1.000"),
        unit=item.unit or "pcs",
        min_threshold=item.min_threshold,
        preferred_quantity=item.preferred_quantity,
        max_quantity=item.max_quantity,
        condition=item.condition,
        asset_status=item.asset_status or "AVAILABLE",
        current_holder_name=item.current_holder_name,
        current_holder_user_id=item.current_holder_user_id,
        last_seen_at=item.last_seen_at,
        last_seen_by=item.last_seen_by,
        last_seen_location_id=item.last_seen_location_id,
        expiry_date=item.expiry_date,
        status=item.status or "GOOD",
        expiry_status=item.expiry_status or "NORMAL",
        notes=item.notes,
        brand=item.brand,
        model_number=item.model_number,
        serial_number=item.serial_number,
        barcode=item.barcode,
        qr_code_identifier=item.qr_code_identifier,
        purchase_date=item.purchase_date,
        purchase_price=item.purchase_price,
        purchase_store=item.purchase_store,
        warranty_expiry_date=item.warranty_expiry_date,
        warranty_status=calculate_warranty_status(item.warranty_expiry_date),
        warranty_notes=item.warranty_notes,
        photo_url=item.photo_url,
        receipt_url=item.receipt_url,
        manual_url=item.manual_url,
        last_serviced_at=item.last_serviced_at,
        next_service_due_at=item.next_service_due_at,
        service_notes=item.service_notes,
        created_by=item.created_by,
        created_at=item.created_at or now,
        updated_at=item.updated_at or now
    )


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
    barcode: Optional[str] = Query(None),
    serial_number: Optional[str] = Query(None),
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
    if barcode:
        filters.append(InventoryItemModel.barcode == barcode.strip())
    if serial_number:
        filters.append(InventoryItemModel.serial_number == serial_number.strip())
    if search:
        s = f"%{search.strip()}%"
        filters.append(
            or_(
                InventoryItemModel.name.ilike(s),
                InventoryItemModel.description.ilike(s),
                InventoryItemModel.location_path.ilike(s),
                InventoryItemModel.current_holder_name.ilike(s),
                InventoryItemModel.notes.ilike(s),
                InventoryItemModel.brand.ilike(s),
                InventoryItemModel.model_number.ilike(s),
                InventoryItemModel.serial_number.ilike(s),
                InventoryItemModel.barcode.ilike(s),
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
        to_inventory_item_dto(i, path_map)
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
        # Extended Asset Tracking & Home Memory
        brand=payload.brand,
        model_number=payload.model_number,
        serial_number=payload.serial_number,
        barcode=payload.barcode,
        qr_code_identifier=payload.qr_code_identifier,
        purchase_date=payload.purchase_date,
        purchase_price=payload.purchase_price,
        purchase_store=payload.purchase_store,
        warranty_expiry_date=payload.warranty_expiry_date,
        warranty_notes=payload.warranty_notes,
        photo_url=payload.photo_url,
        receipt_url=payload.receipt_url,
        manual_url=payload.manual_url,
        last_serviced_at=payload.last_serviced_at,
        next_service_due_at=payload.next_service_due_at,
        service_notes=payload.service_notes,
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
        data=to_inventory_item_dto(new_item, {new_item.location_id: loc_path} if new_item.location_id else None, cat_name)
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
    return ApiSuccessResponse(data=to_inventory_item_dto(item, path_map))


@router.get("/items/{item_id}/qr-label", response_model=ApiSuccessResponse[QRLabelResponse])
async def get_item_qr_label(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
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

    path_map = await build_location_path_map(db, home_ctx.home_id)
    loc_path = path_map.get(item.location_id) if item.location_id else "Unassigned"
    qr_payload = item.qr_code_identifier or f"OZHZO:ASSET:{home_ctx.home_id}:{item.id}"

    return ApiSuccessResponse(
        data=QRLabelResponse(
            item_id=item.id,
            home_id=item.home_id,
            item_name=item.name,
            item_type=item.item_type,
            location_path=loc_path,
            serial_number=item.serial_number,
            barcode=item.barcode,
            qr_payload=qr_payload,
            generated_at=datetime.now(timezone.utc)
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

    # Extended Asset Tracking & Home Memory
    if payload.brand is not None:
        item.brand = payload.brand
    if payload.model_number is not None:
        item.model_number = payload.model_number
    if payload.serial_number is not None:
        item.serial_number = payload.serial_number
    if payload.barcode is not None:
        item.barcode = payload.barcode
    if payload.qr_code_identifier is not None:
        item.qr_code_identifier = payload.qr_code_identifier
    if payload.purchase_date is not None:
        item.purchase_date = payload.purchase_date
    if payload.purchase_price is not None:
        item.purchase_price = payload.purchase_price
    if payload.purchase_store is not None:
        item.purchase_store = payload.purchase_store
    if payload.warranty_expiry_date is not None:
        item.warranty_expiry_date = payload.warranty_expiry_date
    if payload.warranty_notes is not None:
        item.warranty_notes = payload.warranty_notes
    if payload.photo_url is not None:
        item.photo_url = payload.photo_url
    if payload.receipt_url is not None:
        item.receipt_url = payload.receipt_url
    if payload.manual_url is not None:
        item.manual_url = payload.manual_url
    if payload.last_serviced_at is not None:
        item.last_serviced_at = payload.last_serviced_at
    if payload.next_service_due_at is not None:
        item.next_service_due_at = payload.next_service_due_at
    if payload.service_notes is not None:
        item.service_notes = payload.service_notes

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

    return ApiSuccessResponse(data=to_inventory_item_dto(item, path_map, cat_name))


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


@router.post("/items/{item_id}/consume", response_model=ApiSuccessResponse[InventoryItemDTO])
async def consume_inventory_item(
    item_id: UUID,
    payload: ConsumeStockRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick usage / stock reduction. Decreases quantity by used amount and logs stock movement.
    """
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    prev_qty = item.quantity
    used_qty = payload.quantity
    new_qty = max(Decimal("0.000"), prev_qty - used_qty)
    now = datetime.now(timezone.utc)

    movement = StockMovementModel(
        home_id=home_ctx.home_id,
        item_id=item.id,
        movement_type="CONSUME",
        quantity_delta=-used_qty,
        previous_quantity=prev_qty,
        resulting_quantity=new_qty,
        reason=payload.notes or "Quick stock consumption",
        performed_by=home_ctx.user.id,
        created_at=now
    )
    db.add(movement)

    item.quantity = new_qty
    item.status = calculate_stock_status(new_qty, item.min_threshold)
    item.updated_at = now

    await db.commit()
    path_map = await build_location_path_map(db, home_ctx.home_id)
    cat_name = (await db.get(InventoryCategoryModel, item.category_id)).name if item.category_id else None
    return ApiSuccessResponse(data=to_inventory_item_dto(item, path_map, cat_name))


@router.post("/items/{item_id}/restock", response_model=ApiSuccessResponse[InventoryItemDTO])
async def restock_inventory_item(
    item_id: UUID,
    payload: RestockStockRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick restocking. Increases quantity and logs stock movement.
    """
    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    prev_qty = item.quantity
    add_qty = payload.quantity
    new_qty = prev_qty + add_qty
    now = datetime.now(timezone.utc)

    movement = StockMovementModel(
        home_id=home_ctx.home_id,
        item_id=item.id,
        movement_type="RESTOCK",
        quantity_delta=add_qty,
        previous_quantity=prev_qty,
        resulting_quantity=new_qty,
        reason=payload.notes or "Quick stock restock",
        performed_by=home_ctx.user.id,
        created_at=now
    )
    db.add(movement)

    item.quantity = new_qty
    item.status = calculate_stock_status(new_qty, item.min_threshold)
    item.updated_at = now

    await db.commit()
    path_map = await build_location_path_map(db, home_ctx.home_id)
    cat_name = (await db.get(InventoryCategoryModel, item.category_id)).name if item.category_id else None
    return ApiSuccessResponse(data=to_inventory_item_dto(item, path_map, cat_name))


@router.post("/items/{item_id}/add-to-shopping", response_model=ApiSuccessResponse[MessageResponse])
async def add_inventory_item_to_shopping(
    item_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Suggests / Adds a low-stock inventory item directly onto the Home's Purchase List.
    """
    from src.infrastructure.database.models import PurchaseItemModel

    query = select(InventoryItemModel).where(
        InventoryItemModel.id == item_id,
        InventoryItemModel.home_id == home_ctx.home_id,
        InventoryItemModel.deleted_at == None
    )
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    # Check if active item on purchase list already exists
    exist_q = select(PurchaseItemModel).where(
        PurchaseItemModel.home_id == home_ctx.home_id,
        PurchaseItemModel.inventory_item_id == item.id,
        PurchaseItemModel.status == "PENDING"
    )
    existing_p = (await db.execute(exist_q)).scalar_one_or_none()
    if existing_p:
        return ApiSuccessResponse(
            data=MessageResponse(message=f"'{item.name}' is already on your shopping list.")
        )

    needed_qty = max(Decimal("1.000"), (item.preferred_quantity or item.min_threshold or Decimal("1.000")) - item.quantity)
    if needed_qty <= 0:
        needed_qty = Decimal("1.000")

    now = datetime.now(timezone.utc)
    new_purchase_item = PurchaseItemModel(
        id=uuid4(),
        home_id=home_ctx.home_id,
        inventory_item_id=item.id,
        name=item.name,
        quantity=needed_qty,
        unit=item.unit or "pcs",
        notes=f"Low stock restock request (current: {item.quantity} {item.unit})",
        status="PENDING",
        added_by=home_ctx.user.id,
        version=1,
        created_at=now,
        updated_at=now
    )
    db.add(new_purchase_item)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Added '{item.name}' ({needed_qty} {item.unit}) to the shopping list.")
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

    return ApiSuccessResponse(data=to_inventory_item_dto(item, path_map, cat_name))


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
