from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import TaskTemplateModel, UserModel
from src.schemas.common import ApiSuccessResponse
from src.schemas.task import (
    CreateTaskTemplateRequest,
    TaskTemplateDTO
)

router = APIRouter(prefix="/task-templates", tags=["Task Templates"])

DEFAULT_HOUSEHOLD_TASK_TEMPLATES = [
    {
        "name": "Clean Water Filter",
        "default_category_name": "Maintenance",
        "default_priority": "NORMAL",
        "default_recurrence_type": "CUSTOM_DAYS",
        "default_interval_days": 30,
        "description": "Replace sediment filter and sanitize storage tank",
        "sort_order": 1
    },
    {
        "name": "Service AC",
        "default_category_name": "Maintenance",
        "default_priority": "NORMAL",
        "default_recurrence_type": "CUSTOM_DAYS",
        "default_interval_days": 180,
        "description": "Clean air filters, check gas pressure and outdoor compressor",
        "sort_order": 2
    },
    {
        "name": "Change Bedsheets & Linens",
        "default_category_name": "Cleaning",
        "default_priority": "NORMAL",
        "default_recurrence_type": "WEEKLY",
        "default_interval_days": 7,
        "description": "Wash and replace master and guest bedroom sheets",
        "sort_order": 3
    },
    {
        "name": "Deep Clean Kitchen",
        "default_category_name": "Cleaning",
        "default_priority": "NORMAL",
        "default_recurrence_type": "CUSTOM_DAYS",
        "default_interval_days": 30,
        "description": "Degrease stove hood, sanitize countertops, wipe microwave",
        "sort_order": 4
    },
    {
        "name": "Car Maintenance & Oil Check",
        "default_category_name": "Vehicle",
        "default_priority": "NORMAL",
        "default_recurrence_type": "CUSTOM_DAYS",
        "default_interval_days": 180,
        "description": "Check engine oil level, tire pressure, wiper fluid",
        "sort_order": 5
    },
    {
        "name": "Smoke & Gas Detector Battery Check",
        "default_category_name": "Safety",
        "default_priority": "HIGH",
        "default_recurrence_type": "CUSTOM_DAYS",
        "default_interval_days": 180,
        "description": "Test alarm buzzer and replace 9V backup batteries",
        "sort_order": 6
    },
    {
        "name": "Pest Control Inspection",
        "default_category_name": "Maintenance",
        "default_priority": "NORMAL",
        "default_recurrence_type": "CUSTOM_DAYS",
        "default_interval_days": 90,
        "description": "Inspect perimeter and spray anti-termite/cockroach barrier",
        "sort_order": 7
    },
    {
        "name": "Pay School Tuition Fee",
        "default_category_name": "Bills",
        "default_priority": "HIGH",
        "default_recurrence_type": "MONTHLY",
        "default_interval_days": 30,
        "description": "Pay monthly tuition and school transport fees",
        "sort_order": 8
    },
    {
        "name": "Water Garden & Balcony Plants",
        "default_category_name": "Garden",
        "default_priority": "NORMAL",
        "default_recurrence_type": "DAILY",
        "default_interval_days": 1,
        "description": "Water indoor succulents and outdoor garden pots",
        "sort_order": 9
    }
]


async def ensure_default_task_templates(db: AsyncSession):
    q = select(TaskTemplateModel).limit(1)
    res = (await db.execute(q)).scalar_one_or_none()
    if not res:
        for tpl_data in DEFAULT_HOUSEHOLD_TASK_TEMPLATES:
            db.add(TaskTemplateModel(
                name=tpl_data["name"],
                default_category_name=tpl_data["default_category_name"],
                default_priority=tpl_data["default_priority"],
                default_recurrence_type=tpl_data["default_recurrence_type"],
                default_interval_days=tpl_data["default_interval_days"],
                description=tpl_data["description"],
                sort_order=tpl_data["sort_order"],
                is_active=True
            ))
        await db.commit()


@router.get("", response_model=ApiSuccessResponse[List[TaskTemplateDTO]])
async def list_task_templates(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_default_task_templates(db)
    query = select(TaskTemplateModel).where(TaskTemplateModel.is_active == True).order_by(TaskTemplateModel.sort_order.asc(), TaskTemplateModel.name.asc())
    templates = (await db.execute(query)).scalars().all()

    dtos = [
        TaskTemplateDTO(
            id=t.id,
            name=t.name,
            default_category_name=t.default_category_name,
            default_priority=t.default_priority,
            default_recurrence_type=t.default_recurrence_type,
            default_interval_days=t.default_interval_days,
            description=t.description,
            is_active=t.is_active,
            sort_order=t.sort_order,
            created_at=t.created_at,
            updated_at=t.updated_at
        ) for t in templates
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("", response_model=ApiSuccessResponse[TaskTemplateDTO], status_code=status.HTTP_201_CREATED)
async def create_task_template(
    payload: CreateTaskTemplateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tpl = TaskTemplateModel(
        name=payload.name,
        default_category_name=payload.default_category_name or "Maintenance",
        default_priority=payload.default_priority or "NORMAL",
        default_recurrence_type=payload.default_recurrence_type or "NONE",
        default_interval_days=payload.default_interval_days,
        description=payload.description,
        sort_order=payload.sort_order or 0,
        is_active=payload.is_active if payload.is_active is not None else True
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)

    return ApiSuccessResponse(
        data=TaskTemplateDTO(
            id=tpl.id,
            name=tpl.name,
            default_category_name=tpl.default_category_name,
            default_priority=tpl.default_priority,
            default_recurrence_type=tpl.default_recurrence_type,
            default_interval_days=tpl.default_interval_days,
            description=tpl.description,
            is_active=tpl.is_active,
            sort_order=tpl.sort_order,
            created_at=tpl.created_at,
            updated_at=tpl.updated_at
        )
    )
