from datetime import datetime, timezone
from typing import List, Optional
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
    InventoryItemDTO,
    LocationDTO,
    LocationTreeDTO,
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


@router.get("", response_model=ApiSuccessResponse[List[LocationDTO]])
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


@router.delete("/{location_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_location(
    location_id: UUID,
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

    loc.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Location '{loc.name}' has been archived.")
    )
