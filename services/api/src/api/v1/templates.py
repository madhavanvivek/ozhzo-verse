from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import InventoryTemplateModel, UserModel
from src.schemas.common import ApiSuccessResponse, MessageResponse
from src.schemas.inventory import (
    InventoryTemplateDTO,
    CreateInventoryTemplateRequest,
    UpdateInventoryTemplateRequest
)

router = APIRouter(tags=["Inventory Templates"])

DEFAULT_TEMPLATES = [
    {"name": "Rice", "default_category_name": "Pantry", "default_unit": "kg", "description": "Raw basmati, sona masoori, or brown rice"},
    {"name": "Sugar", "default_category_name": "Pantry", "default_unit": "kg", "description": "Refined white or brown cane sugar"},
    {"name": "Salt", "default_category_name": "Pantry", "default_unit": "kg", "description": "Table salt or rock salt"},
    {"name": "Wheat Flour (Atta)", "default_category_name": "Pantry", "default_unit": "kg", "description": "Whole wheat flour for bread/roti"},
    {"name": "Cooking Oil", "default_category_name": "Pantry", "default_unit": "L", "description": "Vegetable, sunflower, or olive oil"},
    {"name": "Milk", "default_category_name": "Refrigerator", "default_unit": "L", "description": "Fresh dairy or plant-based milk"},
    {"name": "Butter", "default_category_name": "Refrigerator", "default_unit": "pack", "description": "Salted or unsalted dairy butter"},
    {"name": "Eggs", "default_category_name": "Refrigerator", "default_unit": "dozen", "description": "Farm fresh chicken eggs"},
    {"name": "Bread", "default_category_name": "Pantry", "default_unit": "pack", "description": "Whole wheat or sandwich loaf"},
    {"name": "Toothpaste", "default_category_name": "Personal Care", "default_unit": "pcs", "description": "Dental hygiene toothpaste tube"},
    {"name": "Detergent", "default_category_name": "Cleaning", "default_unit": "kg", "description": "Laundry washing powder or liquid"},
    {"name": "Dishwashing Liquid", "default_category_name": "Cleaning", "default_unit": "bottle", "description": "Dish and utensil cleaning soap"},
    {"name": "Tissue Paper", "default_category_name": "Household", "default_unit": "pack", "description": "Kitchen paper roll or facial box"},
    {"name": "Batteries (AA/AAA)", "default_category_name": "Household", "default_unit": "pack", "description": "Alkaline or rechargeable power cells"},
    {"name": "Light Bulbs", "default_category_name": "Household", "default_unit": "pcs", "description": "LED or standard ceiling bulbs"},
    {"name": "Shampoo", "default_category_name": "Personal Care", "default_unit": "bottle", "description": "Hair care cleansing shampoo"},
    {"name": "Coffee", "default_category_name": "Pantry", "default_unit": "pack", "description": "Ground roast coffee or instant beans"},
    {"name": "Tea Bags / Leaves", "default_category_name": "Pantry", "default_unit": "pack", "description": "Black, green, or herbal tea"},
]


async def ensure_default_templates(db: AsyncSession):
    count_query = select(func.count(InventoryTemplateModel.id))
    count = (await db.execute(count_query)).scalar() or 0
    if count == 0:
        for idx, tpl in enumerate(DEFAULT_TEMPLATES):
            item = InventoryTemplateModel(
                name=tpl["name"],
                default_category_name=tpl["default_category_name"],
                default_unit=tpl["default_unit"],
                description=tpl.get("description"),
                sort_order=idx * 10,
                is_active=True
            )
            db.add(item)
        await db.commit()


@router.get("/inventory/templates", response_model=ApiSuccessResponse[List[InventoryTemplateDTO]])
async def list_inventory_templates(
    search: Optional[str] = Query(None, description="Search template by name"),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    List active Global Inventory Templates for quick household catalog selection.
    """
    await ensure_default_templates(db)

    query = select(InventoryTemplateModel).where(InventoryTemplateModel.is_active == True)
    if search:
        query = query.where(InventoryTemplateModel.name.ilike(f"%{search.strip()}%"))
    query = query.order_by(InventoryTemplateModel.sort_order.asc(), InventoryTemplateModel.name.asc())

    result = await db.execute(query)
    templates = result.scalars().all()

    dtos = [
        InventoryTemplateDTO(
            id=t.id,
            name=t.name,
            default_category_name=t.default_category_name,
            default_unit=t.default_unit,
            description=t.description,
            is_active=t.is_active,
            sort_order=t.sort_order,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in templates
    ]
    return ApiSuccessResponse(data=dtos)


# ==============================================================================
# Super Admin Endpoints
# ==============================================================================

@router.post("/admin/inventory/templates", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[InventoryTemplateDTO])
async def create_global_template(
    payload: CreateInventoryTemplateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_super_admin),
):
    """
    Super Admin creates a new Global Inventory Template.
    """
    existing_query = select(InventoryTemplateModel).where(
        func.lower(InventoryTemplateModel.name) == payload.name.strip().lower()
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A global template named '{payload.name}' already exists."
        )

    new_tpl = InventoryTemplateModel(
        name=payload.name.strip(),
        default_category_name=payload.default_category_name.strip(),
        default_unit=payload.default_unit.strip(),
        description=payload.description.strip() if payload.description else None,
        is_active=payload.is_active,
        sort_order=payload.sort_order
    )
    db.add(new_tpl)
    await db.commit()
    await db.refresh(new_tpl)

    return ApiSuccessResponse(
        data=InventoryTemplateDTO(
            id=new_tpl.id,
            name=new_tpl.name,
            default_category_name=new_tpl.default_category_name,
            default_unit=new_tpl.default_unit,
            description=new_tpl.description,
            is_active=new_tpl.is_active,
            sort_order=new_tpl.sort_order,
            created_at=new_tpl.created_at,
            updated_at=new_tpl.updated_at
        )
    )


@router.patch("/admin/inventory/templates/{template_id}", response_model=ApiSuccessResponse[InventoryTemplateDTO])
async def update_global_template(
    template_id: UUID,
    payload: UpdateInventoryTemplateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_super_admin),
):
    """
    Super Admin updates an existing Global Inventory Template.
    Existing Home inventory records derived from this template remain untouched.
    """
    query = select(InventoryTemplateModel).where(InventoryTemplateModel.id == template_id)
    tpl = (await db.execute(query)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    if payload.name is not None:
        tpl.name = payload.name.strip()
    if payload.default_category_name is not None:
        tpl.default_category_name = payload.default_category_name.strip()
    if payload.default_unit is not None:
        tpl.default_unit = payload.default_unit.strip()
    if payload.description is not None:
        tpl.description = payload.description.strip() if payload.description else None
    if payload.is_active is not None:
        tpl.is_active = payload.is_active
    if payload.sort_order is not None:
        tpl.sort_order = payload.sort_order

    tpl.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tpl)

    return ApiSuccessResponse(
        data=InventoryTemplateDTO(
            id=tpl.id,
            name=tpl.name,
            default_category_name=tpl.default_category_name,
            default_unit=tpl.default_unit,
            description=tpl.description,
            is_active=tpl.is_active,
            sort_order=tpl.sort_order,
            created_at=tpl.created_at,
            updated_at=tpl.updated_at
        )
    )


@router.delete("/admin/inventory/templates/{template_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_global_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_super_admin),
):
    """
    Super Admin deactivates a Global Inventory Template.
    """
    query = select(InventoryTemplateModel).where(InventoryTemplateModel.id == template_id)
    tpl = (await db.execute(query)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    tpl.is_active = False
    tpl.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Global inventory template deactivated."))
