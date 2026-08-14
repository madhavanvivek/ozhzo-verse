from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import BillTemplateModel, UserModel
from src.schemas.bill import BillTemplateDTO, CreateBillTemplateRequest
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/bill-templates", tags=["Bill Templates Catalog"])

COMMON_BILL_TEMPLATES = [
    {
        "name": "Electricity Bill",
        "default_category_name": "Utilities",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Monthly electricity utility payment (e.g. BESCOM, Tata Power, PG&E, DEWA).",
        "sort_order": 1
    },
    {
        "name": "Water & Sewerage Bill",
        "default_category_name": "Utilities",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Municipal or community water and sewerage billing.",
        "sort_order": 2
    },
    {
        "name": "Piped Gas / Cooking Gas Cylinder",
        "default_category_name": "Utilities",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Piped natural gas (PNG) or LPG cylinder refills.",
        "sort_order": 3
    },
    {
        "name": "High-Speed Fiber Internet",
        "default_category_name": "Communication",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Home broadband and Wi-Fi subscription.",
        "sort_order": 4
    },
    {
        "name": "House Rent",
        "default_category_name": "Housing",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Monthly household rental obligation.",
        "sort_order": 5
    },
    {
        "name": "Apartment Maintenance",
        "default_category_name": "Housing",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Building society / community maintenance charges.",
        "sort_order": 6
    },
    {
        "name": "Car & Vehicle Insurance",
        "default_category_name": "Insurance",
        "default_recurrence_type": "YEARLY",
        "default_interval_days": 365,
        "description": "Annual vehicle comprehensive insurance policy.",
        "sort_order": 7
    },
    {
        "name": "Health & Family Medical Insurance",
        "default_category_name": "Insurance",
        "default_recurrence_type": "YEARLY",
        "default_interval_days": 365,
        "description": "Annual health insurance policy premium.",
        "sort_order": 8
    },
    {
        "name": "Property Tax / Municipal Assessment",
        "default_category_name": "Taxes",
        "default_recurrence_type": "YEARLY",
        "default_interval_days": 365,
        "description": "Annual municipal property tax assessment.",
        "sort_order": 9
    },
    {
        "name": "School / College Tuition Fee",
        "default_category_name": "Education",
        "default_recurrence_type": "QUARTERLY",
        "default_interval_days": 90,
        "description": "Quarterly or term school fee payments.",
        "sort_order": 10
    }
]


@router.get("", response_model=ApiSuccessResponse[List[BillTemplateDTO]])
async def list_bill_templates(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Ensure pre-seeded templates exist
    existing = (await db.execute(select(BillTemplateModel))).scalars().all()
    if not existing:
        for tpl_data in COMMON_BILL_TEMPLATES:
            tpl = BillTemplateModel(
                name=tpl_data["name"],
                default_category_name=tpl_data["default_category_name"],
                default_recurrence_type=tpl_data["default_recurrence_type"],
                default_interval_days=tpl_data.get("default_interval_days"),
                description=tpl_data.get("description"),
                sort_order=tpl_data.get("sort_order", 0)
            )
            db.add(tpl)
        await db.commit()
        existing = (await db.execute(select(BillTemplateModel))).scalars().all()

    dtos = [
        BillTemplateDTO(
            id=t.id,
            name=t.name,
            default_category_name=t.default_category_name,
            default_recurrence_type=t.default_recurrence_type,
            default_interval_days=t.default_interval_days,
            description=t.description,
            is_active=t.is_active,
            sort_order=t.sort_order,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in sorted(existing, key=lambda x: x.sort_order)
    ]
    return ApiSuccessResponse(data=dtos)
