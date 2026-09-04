import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import HomeContext, require_home_permission
from src.infrastructure.database.models import (
    AuditLogModel,
    AutomationExecutionModel,
    AutomationModel,
    HouseholdRecommendationModel,
)
from src.infrastructure.database.session import get_db
from src.schemas.automations import (
    AIAutomationProposalRequest,
    AIAutomationProposalResponse,
    AutomationCreateRequest,
    AutomationExecutionResponseDTO,
    AutomationResponseDTO,
    AutomationStatus,
    AutomationUpdateRequest,
    HouseholdIntelligenceDashboardDTO,
    HouseholdRecommendationDTO,
)
from src.schemas.common import ApiSuccessResponse
from src.services.ai_automation_service import AIAutomationService
from src.services.automation_engine import automation_engine
from src.services.predictive_insight_engine import PredictiveInsightEngine

router = APIRouter(prefix="/homes/{home_id}", tags=["Household Automations & Intelligence"])


def _map_to_dto(auto: AutomationModel) -> AutomationResponseDTO:
    return AutomationResponseDTO(
        id=str(auto.id),
        home_id=str(auto.home_id),
        created_by=str(auto.created_by) if auto.created_by else None,
        name=auto.name,
        description=auto.description,
        enabled=auto.enabled if auto.enabled is not None else True,
        trigger_type=auto.trigger_type,
        conditions=auto.conditions or {},
        actions=auto.actions or [],
        schedule=auto.schedule or {},
        execution_policy=auto.execution_policy or {},
        last_run_at=auto.last_run_at,
        next_run_at=auto.next_run_at,
        status=auto.status,
        failure_count=auto.failure_count or 0,
        consecutive_failures=auto.consecutive_failures or 0,
        version=auto.version or 1,
        created_at=auto.created_at or datetime.now(timezone.utc),
        updated_at=auto.updated_at or datetime.now(timezone.utc)
    )



def _map_exec_dto(e: AutomationExecutionModel) -> AutomationExecutionResponseDTO:
    return AutomationExecutionResponseDTO(
        id=str(e.id),
        automation_id=str(e.automation_id),
        home_id=str(e.home_id),
        trigger_event=e.trigger_event or {},
        evaluated_conditions=e.evaluated_conditions or {},
        actions_attempted=e.actions_attempted,
        actions_succeeded=e.actions_succeeded,
        actions_failed=e.actions_failed,
        duration_ms=e.duration_ms,
        status=e.status,
        error_details=e.error_details,
        correlation_id=e.correlation_id,
        idempotency_key=e.idempotency_key,
        created_at=e.created_at
    )


# ==============================================================================
# 1. AUTOMATION CRUD & CONTROLS
# ==============================================================================

@router.post("/automations", response_model=ApiSuccessResponse[AutomationResponseDTO])
async def create_automation(
    home_id: UUID,
    request: AutomationCreateRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new home-scoped automation rule.
    """
    conditions_dict = request.conditions.model_dump() if request.conditions else {}
    actions_list = [a.model_dump() for a in request.actions]
    schedule_dict = request.schedule.model_dump() if request.schedule else {}
    policy_dict = request.execution_policy or {}

    new_auto = AutomationModel(
        id=uuid4(),
        home_id=home_id,
        created_by=home_ctx.user.id,
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        trigger_type=request.trigger_type.value,
        conditions=conditions_dict,
        actions=actions_list,
        schedule=schedule_dict,
        execution_policy=policy_dict,
        status=AutomationStatus.ACTIVE.value,
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(new_auto)

    # Audit log
    audit = AuditLogModel(
        id=uuid4(),
        entity_type="AUTOMATION",
        entity_id=new_auto.id,
        action="AUTOMATION_CREATED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"name": new_auto.name, "trigger": new_auto.trigger_type})
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_auto)

    return ApiSuccessResponse(data=_map_to_dto(new_auto))


@router.get("/automations", response_model=ApiSuccessResponse[List[AutomationResponseDTO]])
async def list_automations(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all active automation rules in the current home context.
    """
    stmt = (
        select(AutomationModel)
        .where(
            AutomationModel.home_id == home_id,
            AutomationModel.deleted_at.is_(None)
        )
        .order_by(AutomationModel.created_at.desc())
    )
    automations = (await db.execute(stmt)).scalars().all()
    return ApiSuccessResponse(data=[_map_to_dto(a) for a in automations])


@router.get("/automations/{automation_id}", response_model=ApiSuccessResponse[AutomationResponseDTO])
async def get_automation(
    home_id: UUID,
    automation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves details of a single automation rule.
    """
    stmt = select(AutomationModel).where(
        AutomationModel.id == automation_id,
        AutomationModel.home_id == home_id,
        AutomationModel.deleted_at.is_(None)
    )
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")
    return ApiSuccessResponse(data=_map_to_dto(auto))


@router.patch("/automations/{automation_id}", response_model=ApiSuccessResponse[AutomationResponseDTO])
async def update_automation(
    home_id: UUID,
    automation_id: UUID,
    request: AutomationUpdateRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates an automation rule.
    """
    stmt = select(AutomationModel).where(
        AutomationModel.id == automation_id,
        AutomationModel.home_id == home_id,
        AutomationModel.deleted_at.is_(None)
    )
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")

    if request.name is not None:
        auto.name = request.name
    if request.description is not None:
        auto.description = request.description
    if request.enabled is not None:
        auto.enabled = request.enabled
    if request.trigger_type is not None:
        auto.trigger_type = request.trigger_type.value
    if request.conditions is not None:
        auto.conditions = request.conditions.model_dump()
    if request.actions is not None:
        auto.actions = [a.model_dump() for a in request.actions]
    if request.schedule is not None:
        auto.schedule = request.schedule.model_dump()
    if request.execution_policy is not None:
        auto.execution_policy = request.execution_policy
    if request.status is not None:
        auto.status = request.status.value

    auto.version += 1
    auto.updated_at = datetime.now(timezone.utc)

    audit = AuditLogModel(
        id=uuid4(),
        entity_type="AUTOMATION",
        entity_id=auto.id,
        action="AUTOMATION_UPDATED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"version": auto.version})
    )
    db.add(audit)
    await db.commit()
    await db.refresh(auto)

    return ApiSuccessResponse(data=_map_to_dto(auto))


@router.delete("/automations/{automation_id}", response_model=ApiSuccessResponse[Dict[str, Any]])
async def delete_automation(
    home_id: UUID,
    automation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-deletes an automation rule.
    """
    stmt = select(AutomationModel).where(
        AutomationModel.id == automation_id,
        AutomationModel.home_id == home_id,
        AutomationModel.deleted_at.is_(None)
    )
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")

    auto.deleted_at = datetime.now(timezone.utc)
    auto.status = AutomationStatus.DISABLED.value
    auto.enabled = False

    audit = AuditLogModel(
        id=uuid4(),
        entity_type="AUTOMATION",
        entity_id=auto.id,
        action="AUTOMATION_DELETED",
        performed_by=home_ctx.user.id,
        details=json.dumps({"name": auto.name})
    )
    db.add(audit)
    await db.commit()

    return ApiSuccessResponse(data={"id": str(automation_id), "status": "DELETED"})


@router.post("/automations/{automation_id}/enable", response_model=ApiSuccessResponse[AutomationResponseDTO])
async def enable_automation(
    home_id: UUID,
    automation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Enables an automation rule and resets its error health count.
    """
    stmt = select(AutomationModel).where(
        AutomationModel.id == automation_id,
        AutomationModel.home_id == home_id,
        AutomationModel.deleted_at.is_(None)
    )
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")

    auto.enabled = True
    auto.status = AutomationStatus.ACTIVE.value
    auto.consecutive_failures = 0
    await db.commit()
    await db.refresh(auto)
    return ApiSuccessResponse(data=_map_to_dto(auto))


@router.post("/automations/{automation_id}/disable", response_model=ApiSuccessResponse[AutomationResponseDTO])
async def disable_automation(
    home_id: UUID,
    automation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Pauses / disables an automation rule.
    """
    stmt = select(AutomationModel).where(
        AutomationModel.id == automation_id,
        AutomationModel.home_id == home_id,
        AutomationModel.deleted_at.is_(None)
    )
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")

    auto.enabled = False
    auto.status = AutomationStatus.PAUSED.value
    await db.commit()
    await db.refresh(auto)
    return ApiSuccessResponse(data=_map_to_dto(auto))


@router.post("/automations/{automation_id}/run", response_model=ApiSuccessResponse[AutomationExecutionResponseDTO])
async def run_automation_manually(
    home_id: UUID,
    automation_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually triggers an automation execution passing full safety and permission checks.
    """
    stmt = select(AutomationModel).where(
        AutomationModel.id == automation_id,
        AutomationModel.home_id == home_id,
        AutomationModel.deleted_at.is_(None)
    )
    auto = (await db.execute(stmt)).scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")

    execution = await automation_engine.execute_single_automation(
        db=db,
        automation=auto,
        event_payload={"source": "MANUAL_RUN", "user_id": str(home_ctx.user.id)},
        user_role=home_ctx.role,
        user_id=home_ctx.user.id
    )
    return ApiSuccessResponse(data=_map_exec_dto(execution))


@router.get("/automations/{automation_id}/executions", response_model=ApiSuccessResponse[List[AutomationExecutionResponseDTO]])
async def list_automation_executions(
    home_id: UUID,
    automation_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists execution history for a specific automation rule.
    """
    stmt = (
        select(AutomationExecutionModel)
        .where(
            AutomationExecutionModel.automation_id == automation_id,
            AutomationExecutionModel.home_id == home_id
        )
        .order_by(AutomationExecutionModel.created_at.desc())
        .limit(limit)
    )
    executions = (await db.execute(stmt)).scalars().all()
    return ApiSuccessResponse(data=[_map_exec_dto(e) for e in executions])


# ==============================================================================
# 2. HOUSEHOLD INTELLIGENCE & RECOMMENDATIONS DASHBOARD
# ==============================================================================

@router.get("/intelligence/dashboard", response_model=ApiSuccessResponse[HouseholdIntelligenceDashboardDTO])
async def get_household_intelligence_dashboard(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated household intelligence metrics, active automations, predicted patterns, and recommendations.
    """
    summary = await PredictiveInsightEngine.get_dashboard_summary(db, home_id)
    return ApiSuccessResponse(data=summary)


@router.post("/intelligence/recommendations/{rec_id}/accept", response_model=ApiSuccessResponse[Dict[str, Any]])
async def accept_recommendation(
    home_id: UUID,
    rec_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a proactive household recommendation and executes its suggested action.
    """
    stmt = select(HouseholdRecommendationModel).where(
        HouseholdRecommendationModel.id == rec_id,
        HouseholdRecommendationModel.home_id == home_id
    )
    rec = (await db.execute(stmt)).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    rec.status = "ACCEPTED"
    await db.commit()
    return ApiSuccessResponse(data={"id": str(rec_id), "status": "ACCEPTED"})


@router.post("/intelligence/recommendations/{rec_id}/dismiss", response_model=ApiSuccessResponse[Dict[str, Any]])
async def dismiss_recommendation(
    home_id: UUID,
    rec_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Dismisses a proactive household recommendation.
    """
    stmt = select(HouseholdRecommendationModel).where(
        HouseholdRecommendationModel.id == rec_id,
        HouseholdRecommendationModel.home_id == home_id
    )
    rec = (await db.execute(stmt)).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    rec.status = "DISMISSED"
    await db.commit()
    return ApiSuccessResponse(data={"id": str(rec_id), "status": "DISMISSED"})


# ==============================================================================
# 3. AI AUTOMATION GENERATOR ASSISTANCE
# ==============================================================================

@router.post("/ai/automations/propose", response_model=ApiSuccessResponse[AIAutomationProposalResponse])
async def propose_ai_automation(
    home_id: UUID,
    request: AIAutomationProposalRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
):
    """
    Converts a natural language description into a structured, validated automation proposal for user confirmation.
    """
    proposal = AIAutomationService.propose_automation_from_prompt(request)
    return ApiSuccessResponse(data=proposal)
