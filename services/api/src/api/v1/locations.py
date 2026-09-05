from datetime import datetime, timezone
from typing import Any, List, Optional, Union
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.core.locations import build_location_path_map, build_location_tree
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AuditLogModel,
    InventoryItemModel,
    LocationModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.inventory import (
    CreateLocationRequest,
    CreateLocationTypeRequest,
    InventoryItemDTO,
    LocationDTO,
    LocationTreeDTO,
    LocationTypeDTO,
    MessageResponse,
    UpdateLocationRequest
)

router = APIRouter(prefix="/homes/{home_id}/locations", tags=["Locations"])


def to_location_dto(loc: LocationModel, path: Optional[str] = None, item_count: int = 0) -> LocationDTO:
    now = datetime.now(timezone.utc)
    return LocationDTO(
        id=loc.id or uuid4(),
        home_id=loc.home_id or uuid4(),
        parent_id=loc.parent_id,
        name=loc.name or "Location",
        location_type=loc.location_type or "ROOM",
        description=loc.description,
        icon=loc.icon,
        sort_order=loc.sort_order if loc.sort_order is not None else 0,
        is_active=bool(loc.is_active) if loc.is_active is not None else True,
        path=path or loc.name or "Location",
        item_count=item_count,
        created_at=loc.created_at or now,
        updated_at=loc.updated_at or now
    )


@router.get("", response_model=ApiSuccessResponse[Union[List[LocationTreeDTO], List[LocationDTO]]])
async def list_locations(
    as_tree: bool = Query(False, description="Return nested hierarchy tree instead of flat list"),
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(LocationModel)
        .options(selectinload(LocationModel.items))
        .where(
            LocationModel.home_id == home_ctx.home_id,
            LocationModel.deleted_at == None
        )
        .order_by(LocationModel.sort_order.asc(), LocationModel.name.asc())
    )
    result = await db.execute(query)
    locations = result.scalars().all()

    path_map = await build_location_path_map(db, home_ctx.home_id)

    if as_tree:
        tree = build_location_tree(locations, path_map)
        return ApiSuccessResponse(data=tree)

    dtos = [
        to_location_dto(
            loc,
            path=path_map.get(loc.id, loc.name),
            item_count=len([i for i in loc.items if i.deleted_at is None]) if loc.items else 0
        )
        for loc in locations
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[LocationDTO])
async def create_location(
    payload: CreateLocationRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:create")),
    db: AsyncSession = Depends(get_db),
):
    # Validate parent_id belongs to the same Home
    if payload.parent_id:
        parent_query = select(LocationModel).where(
            LocationModel.id == payload.parent_id,
            LocationModel.home_id == home_ctx.home_id,
            LocationModel.deleted_at == None
        )
        parent_res = await db.execute(parent_query)
        if not parent_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent location not found or belongs to another Home."
            )

    # Check duplicate sibling name in same parent
    dup_query = select(LocationModel).where(
        LocationModel.home_id == home_ctx.home_id,
        LocationModel.parent_id == payload.parent_id,
        LocationModel.name.ilike(payload.name.strip()),
        LocationModel.deleted_at == None
    )
    dup_res = await db.execute(dup_query)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A location named '{payload.name}' already exists under this parent."
        )

    new_loc = LocationModel(
        home_id=home_ctx.home_id,
        parent_id=payload.parent_id,
        name=payload.name.strip(),
        location_type=payload.location_type,
        description=payload.description,
        icon=payload.icon,
        sort_order=payload.sort_order,
        created_by=home_ctx.user.id
    )
    db.add(new_loc)
    await db.commit()

    path_map = await build_location_path_map(db, home_ctx.home_id)

    return ApiSuccessResponse(
        data=to_location_dto(new_loc, path=path_map.get(new_loc.id, new_loc.name))
    )


@router.get("/{location_id}", response_model=ApiSuccessResponse[LocationDTO])
async def get_location(
    location_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(LocationModel)
        .options(selectinload(LocationModel.items))
        .where(
            LocationModel.id == location_id,
            LocationModel.home_id == home_ctx.home_id,
            LocationModel.deleted_at == None
        )
    )
    result = await db.execute(query)
    loc = result.scalar_one_or_none()

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found.")

    path_map = await build_location_path_map(db, home_ctx.home_id)

    return ApiSuccessResponse(
        data=to_location_dto(
            loc,
            path=path_map.get(loc.id, loc.name),
            item_count=len([i for i in loc.items if i.deleted_at is None]) if loc.items else 0
        )
    )


@router.patch("/{location_id}", response_model=ApiSuccessResponse[LocationDTO])
async def update_location(
    location_id: UUID,
    payload: UpdateLocationRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(LocationModel).where(
        LocationModel.id == location_id,
        LocationModel.home_id == home_ctx.home_id,
        LocationModel.deleted_at == None
    )
    result = await db.execute(query)
    loc = result.scalar_one_or_none()

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found.")

    if payload.parent_id is not None:
        if payload.parent_id == loc.id:
            raise HTTPException(status_code=400, detail="A location cannot be its own parent.")
        parent_res = await db.execute(
            select(LocationModel).where(
                LocationModel.id == payload.parent_id,
                LocationModel.home_id == home_ctx.home_id,
                LocationModel.deleted_at == None
            )
        )
        if not parent_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Parent location not found or invalid.")
        loc.parent_id = payload.parent_id

    if payload.name is not None:
        loc.name = payload.name.strip()
    if payload.location_type is not None:
        loc.location_type = payload.location_type
    if payload.description is not None:
        loc.description = payload.description
    if payload.icon is not None:
        loc.icon = payload.icon
    if payload.sort_order is not None:
        loc.sort_order = payload.sort_order
    if payload.is_active is not None:
        loc.is_active = payload.is_active

    loc.updated_at = datetime.now(timezone.utc)
    await db.commit()

    path_map = await build_location_path_map(db, home_ctx.home_id)

    return ApiSuccessResponse(
        data=to_location_dto(loc, path=path_map.get(loc.id, loc.name))
    )


DEFAULT_LOCATION_TYPES = [
    {"name": "Room / Area", "code": "ROOM", "description": "Living Room, Kitchen, Master Bedroom, Hallway", "icon": "door"},
    {"name": "Cupboard / Cabinet", "code": "CUPBOARD", "description": "Kitchen cabinet, Wardrobe, Bathroom cabinet", "icon": "cabinet"},
    {"name": "Furniture", "code": "FURNITURE", "description": "Bed, Desk, Dining table, Side table", "icon": "bed"},
    {"name": "Shelf / Rack", "code": "SHELF", "description": "Bookshelf, Storage rack, Shoe rack", "icon": "layers"},
    {"name": "Box / Container / Bin", "code": "CONTAINER", "description": "Plastic tote, Tool box, Storage bin", "icon": "box"},
    {"name": "Kitchen Pantry", "code": "PANTRY", "description": "Food and ingredient storage area", "icon": "shopping-bag"},
    {"name": "Storage Zone", "code": "ZONE", "description": "Garage, Attic, Basement, Shed", "icon": "archive"},
    {"name": "Freezer Section", "code": "FREEZER", "description": "Freezer drawer, Deep freezer", "icon": "thermometer"},
    {"name": "Tool Rack", "code": "TOOL_RACK", "description": "Workshop wall, Tool holder", "icon": "wrench"},
    {"name": "Medicine Cabinet", "code": "MEDICINE", "description": "First aid and pharmaceutical storage", "icon": "cross"},
    {"name": "Travel Bag", "code": "BAG", "description": "Luggage, Backpack, Travel kit", "icon": "briefcase"},
    {"name": "Document Folder", "code": "FOLDER", "description": "Important papers and documents file", "icon": "folder"},
]


@router.delete("/{location_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_location(
    location_id: UUID,
    force: bool = Query(False, description="Force delete even if items are inside"),
    home_ctx: HomeContext = Depends(require_home_permission("inventory:delete")),
    db: AsyncSession = Depends(get_db),
):
    query = select(LocationModel).where(
        LocationModel.id == location_id,
        LocationModel.home_id == home_ctx.home_id,
        LocationModel.deleted_at == None
    )
    result = await db.execute(query)
    loc = result.scalar_one_or_none()

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found.")

    # Safety check: active items attached
    item_count_query = select(func.count(InventoryItemModel.id)).where(
        InventoryItemModel.location_id == location_id,
        InventoryItemModel.deleted_at == None
    )
    raw_cnt = (await db.execute(item_count_query)).scalar()
    item_count = raw_cnt if isinstance(raw_cnt, int) else 0
    if item_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location '{loc.name}' contains {item_count} active item(s). Reassign them first or set force=true."
        )

    loc.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Location '{loc.name}' has been archived.")
    )


# ------------------------------------------------------------------------------
# Custom Location Types Management
# ------------------------------------------------------------------------------

types_router = APIRouter(prefix="/homes/{home_id}/location-types", tags=["Location Types"])


@types_router.get("", response_model=ApiSuccessResponse[List[LocationTypeDTO]])
async def list_location_types(
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all default location types + custom location types scoped to this Home workspace.
    """
    from src.infrastructure.database.models import CustomLocationTypeModel

    # Query custom location types for this home
    query = select(CustomLocationTypeModel).where(
        CustomLocationTypeModel.home_id == home_ctx.home_id,
        CustomLocationTypeModel.deleted_at == None,
        CustomLocationTypeModel.is_active == True
    ).order_by(CustomLocationTypeModel.name.asc())

    custom_types = (await db.execute(query)).scalars().all()

    dtos: List[LocationTypeDTO] = []

    # 1. Add system defaults
    for dt in DEFAULT_LOCATION_TYPES:
        dtos.append(
            LocationTypeDTO(
                name=dt["name"],
                code=dt["code"],
                description=dt.get("description"),
                icon=dt.get("icon"),
                is_system_default=True
            )
        )

    # 2. Add home's custom types
    for ct in custom_types:
        dtos.append(
            LocationTypeDTO(
                id=ct.id,
                home_id=ct.home_id,
                name=ct.name,
                code=ct.code,
                description=ct.description,
                icon=ct.icon,
                is_system_default=False,
                created_at=ct.created_at
            )
        )

    return ApiSuccessResponse(data=dtos)


@types_router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[LocationTypeDTO])
async def create_custom_location_type(
    payload: CreateLocationTypeRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new custom location type scoped specifically to this Home.
    """
    from src.infrastructure.database.models import CustomLocationTypeModel
    import re

    clean_name = payload.name.strip()
    code = (payload.code.strip().upper() if payload.code else re.sub(r'[^A-Z0-9_]', '_', clean_name.upper()))

    # Check duplicate code within the home
    existing_query = select(CustomLocationTypeModel).where(
        CustomLocationTypeModel.home_id == home_ctx.home_id,
        CustomLocationTypeModel.code == code,
        CustomLocationTypeModel.deleted_at == None
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location type with code '{code}' already exists for this home."
        )

    new_type = CustomLocationTypeModel(
        id=uuid4(),
        home_id=home_ctx.home_id,
        name=clean_name,
        code=code,
        description=payload.description,
        icon=payload.icon or "tag",
        is_active=True,
        created_by=home_ctx.user.id
    )
    db.add(new_type)
    await db.commit()

    return ApiSuccessResponse(
        data=LocationTypeDTO(
            id=new_type.id,
            home_id=new_type.home_id,
            name=new_type.name,
            code=new_type.code,
            description=new_type.description,
            icon=new_type.icon,
            is_system_default=False,
            created_at=new_type.created_at
        )
    )


@types_router.delete("/{type_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_custom_location_type(
    type_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive / delete a custom location type belonging to this Home.
    """
    from src.infrastructure.database.models import CustomLocationTypeModel

    query = select(CustomLocationTypeModel).where(
        CustomLocationTypeModel.id == type_id,
        CustomLocationTypeModel.home_id == home_ctx.home_id,
        CustomLocationTypeModel.deleted_at == None
    )
    c_type = (await db.execute(query)).scalar_one_or_none()
    if not c_type:
        raise HTTPException(status_code=404, detail="Custom location type not found.")

    c_type.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Location type '{c_type.name}' has been archived.")
    )
