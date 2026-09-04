from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import HomeContext, require_home_permission
from src.infrastructure.database.session import get_db
from src.schemas.common import ApiSuccessResponse
from src.schemas.intelligence_memory import (
    AIConversationTurnRequest,
    AIConversationTurnResponse,
    HouseholdDigestDTO,
    HouseholdMemoryCreateRequest,
    HouseholdMemoryResponseDTO,
    HouseholdMemoryUpdateRequest,
    MemoryCategory,
    MemoryStatus,
    PersonalizationPreferenceDTO,
    PersonalizationPreferenceUpdateRequest,
)
from src.services.ai_agent_service import AIAgentService
from src.services.ai_agent_tool_registry import AIAgentToolRegistry
from src.services.household_memory_service import HouseholdMemoryService
from src.services.personalization_service import PersonalizationService

router = APIRouter(prefix="/homes/{home_id}", tags=["Household Memory & Personalization"])


# ==============================================================================
# 1. HOUSEHOLD MEMORY ENDPOINTS
# ==============================================================================

@router.post("/memories", response_model=ApiSuccessResponse[HouseholdMemoryResponseDTO])
async def create_household_memory(
    home_id: UUID,
    request: HouseholdMemoryCreateRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates or updates a long-term household memory or user preference.
    """
    mem_dto = await HouseholdMemoryService.create_memory(
        db=db,
        home_id=home_id,
        request=request,
        user_id=home_ctx.user.id,
    )
    return ApiSuccessResponse(data=mem_dto)


@router.get("/memories", response_model=ApiSuccessResponse[List[HouseholdMemoryResponseDTO]])
async def list_household_memories(
    home_id: UUID,
    category: Optional[MemoryCategory] = None,
    status: Optional[MemoryStatus] = None,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists active household memories scoped to the current home context.
    """
    memories = await HouseholdMemoryService.list_memories(
        db=db,
        home_id=home_id,
        category=category,
        status=status,
        user_id=home_ctx.user.id,
        include_household=True,
    )
    return ApiSuccessResponse(data=memories)


@router.patch("/memories/{memory_id}", response_model=ApiSuccessResponse[HouseholdMemoryResponseDTO])
async def update_household_memory(
    home_id: UUID,
    memory_id: UUID,
    request: HouseholdMemoryUpdateRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates or corrects an existing household memory.
    """
    updated = await HouseholdMemoryService.update_memory(
        db=db,
        home_id=home_id,
        memory_id=memory_id,
        request=request,
        user_id=home_ctx.user.id,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return ApiSuccessResponse(data=updated)


@router.delete("/memories/{memory_id}", response_model=ApiSuccessResponse[Dict[str, Any]])
async def delete_household_memory(
    home_id: UUID,
    memory_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft deletes or archives a household memory.
    """
    deleted = await HouseholdMemoryService.delete_memory(
        db=db,
        home_id=home_id,
        memory_id=memory_id,
        user_id=home_ctx.user.id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return ApiSuccessResponse(data={"id": str(memory_id), "status": "DELETED"})


# ==============================================================================
# 2. PERSONALIZATION PREFERENCE CENTER
# ==============================================================================

@router.get("/personalization", response_model=ApiSuccessResponse[PersonalizationPreferenceDTO])
async def get_personalization_preferences(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves user personalization settings (memory enable/disable, reminder timing).
    """
    prefs = await PersonalizationService.get_or_create_preferences(
        db=db,
        user_id=home_ctx.user.id,
        home_id=home_id,
    )
    return ApiSuccessResponse(data=prefs)


@router.patch("/personalization", response_model=ApiSuccessResponse[PersonalizationPreferenceDTO])
async def update_personalization_preferences(
    home_id: UUID,
    request: PersonalizationPreferenceUpdateRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates user personalization preferences and AI memory controls.
    """
    updated_prefs = await PersonalizationService.update_preferences(
        db=db,
        user_id=home_ctx.user.id,
        home_id=home_id,
        request=request,
    )
    return ApiSuccessResponse(data=updated_prefs)


# ==============================================================================
# 3. HOUSEHOLD INTELLIGENCE DIGEST
# ==============================================================================

@router.get("/intelligence/digest", response_model=ApiSuccessResponse[HouseholdDigestDTO])
async def get_weekly_household_digest(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a personalized weekly summary of household activity, chores, bills, and patterns.
    """
    digest = await PersonalizationService.generate_weekly_digest(
        db=db,
        home_id=home_id,
    )
    return ApiSuccessResponse(data=digest)


# ==============================================================================
# 4. BOUNDED AI AGENT CONVERSATION & PLANNING
# ==============================================================================

@router.post("/ai/agent/chat", response_model=ApiSuccessResponse[AIConversationTurnResponse])
async def process_ai_agent_turn(
    home_id: UUID,
    request: AIConversationTurnRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Processes a multi-turn conversation turn with long-term memory retrieval and planning.
    """
    res = await AIAgentService.process_conversation_turn(
        db=db,
        home_id=home_id,
        request=request,
        user_role=home_ctx.role,
        user_id=home_ctx.user.id,
    )
    return ApiSuccessResponse(data=res)


@router.post("/ai/agent/plans/{session_token}/execute", response_model=ApiSuccessResponse[Dict[str, Any]])
async def execute_confirmed_ai_plan(
    home_id: UUID,
    session_token: str,
    home_ctx: HomeContext = Depends(require_home_permission("home:edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes a multi-step plan confirmed explicitly by the user.
    """
    res = await AIAgentService.execute_confirmed_plan(
        db=db,
        home_id=home_id,
        session_token=session_token,
        user_role=home_ctx.role,
        user_id=home_ctx.user.id,
    )
    return ApiSuccessResponse(data=res)


@router.get("/ai/agent/tools", response_model=ApiSuccessResponse[List[Dict[str, Any]]])
async def list_allowlisted_agent_tools(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
):
    """
    Returns the registry of allowlisted tools available to the AI agent.
    """
    tools = AIAgentToolRegistry.list_tools()
    return ApiSuccessResponse(data=tools)
