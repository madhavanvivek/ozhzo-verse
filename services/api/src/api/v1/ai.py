from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import HomeContext, require_home_permission
from src.infrastructure.database.session import get_db
from src.schemas.ai import (
    AIActionExecutionResult,
    AIChatRequest,
    AIChatResponse,
    AIRecommendationDTO,
    AIUsageMetricsDTO,
)
from src.schemas.common import ApiSuccessResponse
from src.services.ai_assistant_service import ai_assistant_service

router = APIRouter(prefix="/homes/{home_id}/ai", tags=["Household AI Intelligence"])


@router.post("/chat", response_model=ApiSuccessResponse[AIChatResponse])
async def ai_chat_interaction(
    home_id: UUID,
    request: AIChatRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles natural language conversation with the Household AI Assistant.
    Detects intents, constructs authorized home context, and stages action proposals if applicable.
    """
    response = await ai_assistant_service.process_chat(db, home_ctx, request)
    return ApiSuccessResponse(data=response)


@router.post("/actions/{action_id}/confirm", response_model=ApiSuccessResponse[AIActionExecutionResult])
async def confirm_ai_action(
    home_id: UUID,
    action_id: str,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritatively executes a previously staged AI Action Proposal upon explicit user confirmation.
    """
    result = await ai_assistant_service.execute_action_proposal(db, home_ctx, action_id)
    return ApiSuccessResponse(data=result)


@router.post("/actions/{action_id}/reject", response_model=ApiSuccessResponse[Dict[str, Any]])
async def reject_ai_action(
    home_id: UUID,
    action_id: str,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
):
    """
    Rejects and clears a staged action proposal.
    """
    if action_id in ai_assistant_service._staged_proposals:
        del ai_assistant_service._staged_proposals[action_id]
    return ApiSuccessResponse(data={"action_id": action_id, "status": "REJECTED"})


@router.get("/recommendations", response_model=ApiSuccessResponse[List[AIRecommendationDTO]])
async def get_ai_recommendations(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns proactive household recommendations and routines derived from current home state.
    """
    recs = await ai_assistant_service.get_recommendations(db, home_ctx)
    return ApiSuccessResponse(data=recs)


@router.get("/usage", response_model=ApiSuccessResponse[AIUsageMetricsDTO])
async def get_ai_usage_metrics(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
):
    """
    Returns AI usage statistics and cost estimations for the active home.
    """
    usage = ai_assistant_service.get_usage(home_ctx.home_id)
    return ApiSuccessResponse(data=usage)
