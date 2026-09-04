import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.models import (
    AIUsageQuotaModel,
    AIUsageRecordModel,
    AutomationExecutionModel,
    AutomationModel,
    HomeModel,
    SubscriptionAuditLogModel,
    UserModel,
)
from src.infrastructure.database.session import get_db
from src.schemas.admin_operational import (
    AdminAIConfigDTO,
    UpdateAdminAIConfigRequest,
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse

router = APIRouter(prefix="/admin", tags=["Super Admin - AI & Automations Control"])


async def record_audit_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: dict = None,
    new_values: dict = None,
    reason: str = None,
):
    audit_entry = SubscriptionAuditLogModel(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason,
    )
    db.add(audit_entry)


@router.get("/ai/config", response_model=ApiSuccessResponse[AdminAIConfigDTO])
async def get_ai_platform_config(
    super_admin: UserModel = Depends(require_admin_permission("admin:dashboard:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve global AI provider configuration, cost analytics, and active home quotas.
    """
    total_records = (await db.execute(select(func.count(AIUsageRecordModel.id)))).scalar() or 0
    total_cost = (await db.execute(select(func.sum(AIUsageRecordModel.estimated_cost_usd)))).scalar() or Decimal("0.00")
    total_tokens = (await db.execute(select(func.sum(AIUsageRecordModel.total_tokens)))).scalar() or 0
    active_quotas = (await db.execute(select(func.count(AIUsageQuotaModel.id)))).scalar() or 0

    return ApiSuccessResponse(
        data=AdminAIConfigDTO(
            provider="gemini",
            available_providers=["gemini", "anthropic", "openai", "mock"],
            default_model="gemini-2.0-flash",
            daily_request_limit_default=150,
            daily_token_limit_default=150000,
            monthly_cost_limit_usd_default=Decimal("10.00"),
            total_ai_records=total_records,
            total_estimated_cost_usd=float(total_cost),
            total_tokens_consumed=int(total_tokens),
            active_quotas_count=active_quotas,
        )
    )


@router.patch("/ai/config", response_model=ApiSuccessResponse[MessageResponse])
async def update_ai_platform_config(
    payload: UpdateAdminAIConfigRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update global default AI limits and provider settings.
    """
    await record_audit_log(
        db,
        entity_type="AI_PLATFORM_CONFIG",
        entity_id=uuid4(),
        action="UPDATE_AI_CONFIG",
        performed_by=super_admin.id,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
        reason="Super Admin updated platform AI configurations",
    )
    await db.commit()
    return ApiSuccessResponse(data=MessageResponse(message="AI platform operational limits updated successfully."))


@router.get("/automations/quarantine")
async def list_quarantined_automations(
    super_admin: UserModel = Depends(require_admin_permission("admin:dashboard:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    List failed or quarantined automations across all households.
    """
    stmt = (
        select(AutomationModel, HomeModel.name.label("home_name"))
        .join(HomeModel, AutomationModel.home_id == HomeModel.id)
        .where((AutomationModel.status == "ERROR") | (AutomationModel.failure_count > 0))
        .order_by(desc(AutomationModel.failure_count))
        .limit(50)
    )
    res = await db.execute(stmt)
    rows = res.all()

    return ApiSuccessResponse(
        data=[
            {
                "id": str(auto.id),
                "home_id": str(auto.home_id),
                "home_name": home_name,
                "name": auto.name,
                "trigger_type": auto.trigger_type,
                "status": auto.status,
                "enabled": auto.enabled,
                "failure_count": auto.failure_count,
                "consecutive_failures": auto.consecutive_failures,
                "last_run_at": auto.last_run_at.isoformat() if auto.last_run_at else None,
            }
            for auto, home_name in rows
        ]
    )


@router.post("/automations/{automation_id}/restore", response_model=ApiSuccessResponse[MessageResponse])
async def restore_quarantined_automation(
    automation_id: UUID,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset failure counters and restore a quarantined automation to ACTIVE status.
    """
    stmt = select(AutomationModel).where(AutomationModel.id == automation_id)
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found.")

    old_status = auto.status
    auto.status = "ACTIVE"
    auto.failure_count = 0
    auto.consecutive_failures = 0
    auto.enabled = True

    await record_audit_log(
        db,
        entity_type="AUTOMATION",
        entity_id=auto.id,
        action="RESTORE_AUTOMATION",
        performed_by=super_admin.id,
        old_values={"status": old_status},
        new_values={"status": "ACTIVE", "failure_count": 0},
    )

    await db.commit()
    return ApiSuccessResponse(data=MessageResponse(message=f"Automation '{auto.name}' restored to active status."))


@router.post("/automations/{automation_id}/disable", response_model=ApiSuccessResponse[MessageResponse])
async def disable_problematic_automation(
    automation_id: UUID,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Operationally disable a runaway or problematic automation.
    """
    stmt = select(AutomationModel).where(AutomationModel.id == automation_id)
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found.")

    auto.status = "DISABLED"
    auto.enabled = False

    await record_audit_log(
        db,
        entity_type="AUTOMATION",
        entity_id=auto.id,
        action="DISABLE_AUTOMATION",
        performed_by=super_admin.id,
        new_values={"status": "DISABLED", "enabled": False},
    )

    await db.commit()
    return ApiSuccessResponse(data=MessageResponse(message=f"Automation '{auto.name}' administratively disabled."))
