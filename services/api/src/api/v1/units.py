from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    UnitModel,
    InventoryItemModel,
    PurchaseItemModel,
    PurchaseHistoryModel
)
from src.schemas.common import ApiSuccessResponse, MessageResponse
from src.schemas.inventory import (
    UnitDTO,
    CreateUnitRequest,
    UpdateUnitRequest
)

router = APIRouter(prefix="/homes/{home_id}/units", tags=["Units Master"])

DEFAULT_GLOBAL_UNITS = [
    {"name": "Kilogram", "symbol": "kg", "measurement_type": "WEIGHT", "sort_order": 10},
    {"name": "Gram", "symbol": "g", "measurement_type": "WEIGHT", "sort_order": 20},
    {"name": "Liter", "symbol": "L", "measurement_type": "VOLUME", "sort_order": 30},
    {"name": "Milliliter", "symbol": "ml", "measurement_type": "VOLUME", "sort_order": 40},
    {"name": "Piece", "symbol": "pcs", "measurement_type": "COUNT", "sort_order": 50},
    {"name": "Pack / Packet", "symbol": "pack", "measurement_type": "COUNT", "sort_order": 60},
    {"name": "Box", "symbol": "box", "measurement_type": "COUNT", "sort_order": 70},
    {"name": "Bottle", "symbol": "bottle", "measurement_type": "COUNT", "sort_order": 80},
    {"name": "Can", "symbol": "can", "measurement_type": "COUNT", "sort_order": 90},
    {"name": "Dozen", "symbol": "dozen", "measurement_type": "COUNT", "sort_order": 100},
]


async def ensure_global_units(db: AsyncSession):
    count_query = select(func.count(UnitModel.id)).where(UnitModel.home_id == None)
    count = (await db.execute(count_query)).scalar() or 0
    if count == 0:
        for u in DEFAULT_GLOBAL_UNITS:
            db.add(UnitModel(
                home_id=None,
                name=u["name"],
                symbol=u["symbol"],
                measurement_type=u["measurement_type"],
                sort_order=u["sort_order"],
                is_active=True
            ))
        await db.commit()


@router.get("", response_model=ApiSuccessResponse[List[UnitDTO]])
async def list_home_units(
    home_ctx: HomeContext = Depends(require_home_permission("inventory:view")),
    include_inactive: bool = Query(False, description="Include deactivated custom units"),
    db: AsyncSession = Depends(get_db),
):
    """
    List available units for this Home (Global system defaults + Home-custom units).
    """
    await ensure_global_units(db)

    query = select(UnitModel).where(
        or_(
            UnitModel.home_id == None,
            UnitModel.home_id == home_ctx.home_id
        )
    )
    if not include_inactive:
        query = query.where(UnitModel.is_active == True)

    query = query.order_by(UnitModel.sort_order.asc(), UnitModel.name.asc())
    result = await db.execute(query)
    units = result.scalars().all()

    dtos = [
        UnitDTO(
            id=u.id,
            home_id=u.home_id,
            name=u.name,
            symbol=u.symbol,
            measurement_type=u.measurement_type,
            is_active=u.is_active,
            is_global=(u.home_id is None),
            sort_order=u.sort_order,
            created_at=u.created_at,
            updated_at=u.updated_at
        )
        for u in units
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[UnitDTO])
async def create_home_custom_unit(
    payload: CreateUnitRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a custom unit specific to this Home (e.g. 'bundle', 'strip', 'packet').
    """
    symbol_clean = payload.symbol.strip().lower()
    existing_query = select(UnitModel).where(
        or_(
            UnitModel.home_id == None,
            UnitModel.home_id == home_ctx.home_id
        ),
        func.lower(UnitModel.symbol) == symbol_clean
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        if not existing.is_active and existing.home_id == home_ctx.home_id:
            existing.is_active = True
            existing.name = payload.name.strip()
            existing.measurement_type = payload.measurement_type.strip()
            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)
            return ApiSuccessResponse(
                data=UnitDTO(
                    id=existing.id,
                    home_id=existing.home_id,
                    name=existing.name,
                    symbol=existing.symbol,
                    measurement_type=existing.measurement_type,
                    is_active=existing.is_active,
                    is_global=False,
                    sort_order=existing.sort_order,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at
                )
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit with symbol '{payload.symbol}' already exists."
        )

    new_unit = UnitModel(
        home_id=home_ctx.home_id,
        name=payload.name.strip(),
        symbol=payload.symbol.strip(),
        measurement_type=payload.measurement_type.strip(),
        sort_order=payload.sort_order,
        is_active=True
    )
    db.add(new_unit)
    await db.commit()
    await db.refresh(new_unit)

    return ApiSuccessResponse(
        data=UnitDTO(
            id=new_unit.id,
            home_id=new_unit.home_id,
            name=new_unit.name,
            symbol=new_unit.symbol,
            measurement_type=new_unit.measurement_type,
            is_active=new_unit.is_active,
            is_global=False,
            sort_order=new_unit.sort_order,
            created_at=new_unit.created_at,
            updated_at=new_unit.updated_at
        )
    )


@router.patch("/{unit_id}", response_model=ApiSuccessResponse[UnitDTO])
async def update_home_custom_unit(
    unit_id: UUID,
    payload: UpdateUnitRequest,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update or deactivate a Home custom unit.
    Global default units cannot be modified by home members.
    """
    query = select(UnitModel).where(
        UnitModel.id == unit_id,
        UnitModel.home_id == home_ctx.home_id
    )
    unit = (await db.execute(query)).scalar_one_or_none()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom unit not found for this Home."
        )

    if payload.name is not None:
        unit.name = payload.name.strip()
    if payload.symbol is not None:
        unit.symbol = payload.symbol.strip()
    if payload.measurement_type is not None:
        unit.measurement_type = payload.measurement_type.strip()
    if payload.is_active is not None:
        unit.is_active = payload.is_active
    if payload.sort_order is not None:
        unit.sort_order = payload.sort_order

    unit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(unit)

    return ApiSuccessResponse(
        data=UnitDTO(
            id=unit.id,
            home_id=unit.home_id,
            name=unit.name,
            symbol=unit.symbol,
            measurement_type=unit.measurement_type,
            is_active=unit.is_active,
            is_global=False,
            sort_order=unit.sort_order,
            created_at=unit.created_at,
            updated_at=unit.updated_at
        )
    )


@router.delete("/{unit_id}", response_model=ApiSuccessResponse[MessageResponse])
async def deactivate_home_custom_unit(
    unit_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("inventory:delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivates a Home custom unit rather than physical deletion to safeguard historical data integrity.
    """
    query = select(UnitModel).where(
        UnitModel.id == unit_id,
        UnitModel.home_id == home_ctx.home_id
    )
    unit = (await db.execute(query)).scalar_one_or_none()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom unit not found for this Home."
        )

    unit.is_active = False
    unit.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Unit successfully deactivated."))
