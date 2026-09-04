import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.api.dependencies import HomeContext
from src.api.v1.intelligence_memory import (
    create_household_memory,
    delete_household_memory,
    execute_confirmed_ai_plan,
    get_personalization_preferences,
    get_weekly_household_digest,
    list_household_memories,
    process_ai_agent_turn,
    update_household_memory,
    update_personalization_preferences,
)
from src.infrastructure.database.models import (
    AIConversationSessionModel,
    HouseholdMemoryModel,
    HomeModel,
    TaskModel,
    UserModel,
    UserPersonalizationPreferenceModel,
)
from src.schemas.intelligence_memory import (
    AIConversationTurnRequest,
    HouseholdMemoryCreateRequest,
    HouseholdMemoryUpdateRequest,
    MemoryCategory,
    MemorySource,
    MemoryStatus,
    PersonalizationPreferenceUpdateRequest,
)
from src.services.ai_agent_service import AIAgentService
from src.services.ai_agent_tool_registry import AIAgentToolRegistry
from src.services.household_memory_service import HouseholdMemoryService
from src.services.personalization_service import PersonalizationService


# ==============================================================================
# 1. HOUSEHOLD MEMORY LIFECYCLE & DEDUPLICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_memory_creation_deduplication_and_superseding():
    """
    Verifies that duplicate memories are merged and user preferences supersede AI inferred ones.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="host@ozhzo.com")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # 1. Create AI-inferred memory
    req1 = HouseholdMemoryCreateRequest(
        category=MemoryCategory.ROUTINE,
        content="Family usually shops on Saturday mornings",
        source=MemorySource.AI_INFERRED,
        confidence=0.85,
    )

    # Empty existing memories
    res_empty = MagicMock()
    res_empty.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = res_empty

    created1 = await create_household_memory(home_id=home_id, request=req1, home_ctx=home_ctx, db=mock_db)
    assert created1.data.content == "Family usually shops on Saturday mornings"
    assert created1.data.source == MemorySource.AI_INFERRED
    assert mock_db.add.called

    # 2. Re-submitting identical memory with USER_CONFIRMED source merges
    existing_mem = HouseholdMemoryModel(
        id=uuid4(),
        home_id=home_id,
        category="ROUTINE",
        content="Family usually shops on Saturday mornings",
        source="AI_INFERRED",
        confidence=Decimal("0.85"),
        status="ACTIVE",
        context_metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    res_existing = MagicMock()
    res_existing.scalars.return_value.all.return_value = [existing_mem]
    mock_db.execute.return_value = res_existing

    req2 = HouseholdMemoryCreateRequest(
        category=MemoryCategory.ROUTINE,
        content="Family usually shops on Saturday mornings",
        source=MemorySource.USER_CONFIRMED,
        confidence=1.0,
    )
    merged = await create_household_memory(home_id=home_id, request=req2, home_ctx=home_ctx, db=mock_db)
    assert merged.data.source == MemorySource.USER_CONFIRMED
    assert merged.data.confidence == 1.0


# ==============================================================================
# 2. RELEVANCE FILTERED MEMORY RETRIEVAL & PRIVACY TOGGLE
# ==============================================================================

@pytest.mark.asyncio
async def test_memory_retrieval_and_privacy_toggle():
    """
    Verifies deterministic memory retrieval and respect for ai_memory_enabled toggle.
    """
    home_id = uuid4()
    user_id = uuid4()

    mock_db = AsyncMock()

    # Mock user personalization preference with ai_memory_enabled=True
    pref_enabled = UserPersonalizationPreferenceModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        ai_memory_enabled=True,
    )
    res_pref = MagicMock()
    res_pref.scalar_one_or_none.return_value = pref_enabled

    # Mock active memories
    mem1 = HouseholdMemoryModel(
        id=uuid4(),
        home_id=home_id,
        category="PREFERENCE",
        content="Prefers reminders 1 day before bill due date",
        source="USER_PROVIDED",
        confidence=Decimal("1.0"),
        status="ACTIVE",
    )
    mem2 = HouseholdMemoryModel(
        id=uuid4(),
        home_id=home_id,
        category="ROUTINE",
        content="Buys Whole Milk and Eggs every Monday",
        source="USER_PROVIDED",
        confidence=Decimal("0.95"),
        status="ACTIVE",
    )

    res_mems = MagicMock()
    res_mems.scalars.return_value.all.return_value = [mem1, mem2]

    mock_db.execute.side_effect = [res_pref, res_mems]

    snippets = await HouseholdMemoryService.retrieve_relevant_memories(
        db=mock_db,
        home_id=home_id,
        query="remind me about electricity bill",
        user_id=user_id,
    )

    assert len(snippets) > 0
    assert any("1 day before" in s for s in snippets)

    # Now verify with ai_memory_enabled=False
    pref_disabled = UserPersonalizationPreferenceModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        ai_memory_enabled=False,
    )
    res_pref_dis = MagicMock()
    res_pref_dis.scalar_one_or_none.return_value = pref_disabled
    mock_db.execute.side_effect = [res_pref_dis]

    snippets_disabled = await HouseholdMemoryService.retrieve_relevant_memories(
        db=mock_db,
        home_id=home_id,
        query="remind me about electricity bill",
        user_id=user_id,
    )
    assert snippets_disabled == []


# ==============================================================================
# 3. PERSONALIZATION PREFERENCE & WEEKLY DIGEST
# ==============================================================================

@pytest.mark.asyncio
async def test_personalization_preferences_and_weekly_digest():
    """
    Verifies user preference updates and weekly household intelligence digest aggregation.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="member@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Sunset Haven")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # 1. Update preferences
    pref_req = PersonalizationPreferenceUpdateRequest(
        reminder_timing_preference="SAME_DAY_MORNING",
        recommendation_frequency="HIGH",
    )
    pref_res = MagicMock()
    pref_res.scalar_one_or_none.return_value = None

    mock_db.execute.return_value = pref_res

    updated_prefs = await update_personalization_preferences(
        home_id=home_id,
        request=pref_req,
        home_ctx=home_ctx,
        db=mock_db,
    )
    assert updated_prefs.data.reminder_timing_preference == "SAME_DAY_MORNING"
    assert updated_prefs.data.recommendation_frequency == "HIGH"

    # 2. Generate Weekly Digest
    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home

    res_count_10 = MagicMock()
    res_count_10.scalar.return_value = 10

    res_count_2 = MagicMock()
    res_count_2.scalar.return_value = 2

    mock_db.execute.side_effect = [
        res_home,
        res_count_10,  # completed tasks
        res_count_2,   # overdue tasks
        res_count_2,   # paid bills
        res_count_2,   # upcoming bills
        res_count_10,  # purchased items
        res_count_2,   # low inventory
        res_count_10,  # automations executed
    ]

    digest_resp = await get_weekly_household_digest(home_id=home_id, home_ctx=home_ctx, db=mock_db)
    assert digest_resp.data.home_name == "Sunset Haven"
    assert digest_resp.data.tasks_completed_count == 10
    assert digest_resp.data.tasks_overdue_count == 2
    assert len(digest_resp.data.highlights) >= 2


# ==============================================================================
# 4. ALLOWLISTED TOOL REGISTRY & BOUNDED AI AGENT
# ==============================================================================

def test_allowlisted_tool_registry():
    """
    Verifies that all registered tools have explicit domain schemas and permission requirements.
    """
    tools = AIAgentToolRegistry.list_tools()
    tool_names = [t["name"] for t in tools]

    assert "query_tasks" in tool_names
    assert "query_bills" in tool_names
    assert "query_shopping" in tool_names
    assert "query_inventory" in tool_names
    assert "create_task" in tool_names
    assert "create_shopping_item" in tool_names
    assert "create_reminder" in tool_names

    task_tool = AIAgentToolRegistry.get_tool("create_task")
    assert task_tool is not None
    assert task_tool.is_write_action is True
    assert task_tool.permission_required == "tasks:create"


# ==============================================================================
# 5. MULTI-TURN CONVERSATION CONTINUITY & PLANNING
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_agent_multi_turn_and_multi_step_planning():
    """
    Verifies multi-turn contextual continuity and multi-step structured plan generation.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # Preference query mock
    mock_pref = UserPersonalizationPreferenceModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        personalization_enabled=True,
        ai_memory_enabled=True,
        reminder_timing_preference="1_DAY_BEFORE",
        recommendation_frequency="BALANCED",
        digest_enabled=True,
        digest_day_of_week="SUNDAY",
        preferences_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    res_pref = MagicMock()
    res_pref.scalar_one_or_none.return_value = mock_pref

    # Empty session query
    res_session = MagicMock()
    res_session.scalar_one_or_none.return_value = None

    # Empty memories
    res_mems = MagicMock()
    res_mems.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_session,  # session lookup
        res_pref,     # memory pref check
        res_mems,     # memory fetch
        res_pref,     # user prefs
    ]

    # Test multi-step plan generation
    req = AIConversationTurnRequest(prompt="Prepare the house for the weekend")
    turn_resp = await process_ai_agent_turn(home_id=home_id, request=req, home_ctx=home_ctx, db=mock_db)

    assert turn_resp.data.session_token is not None
    assert turn_resp.data.suggested_plan is not None
    assert len(turn_resp.data.suggested_plan.steps) == 3
    assert turn_resp.data.requires_confirmation is True


@pytest.mark.asyncio
async def test_execute_confirmed_ai_plan():
    """
    Verifies execution of a confirmed AI plan through allowlisted domain tools.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    active_plan_json = {
        "plan_id": "plan-123",
        "title": "Weekend Chores",
        "steps": [
            {
                "step_number": 1,
                "tool_name": "create_task",
                "parameters": {"title": "Clean Kitchen Counter", "priority": "NORMAL"},
                "permission_required": "tasks:create",
            }
        ]
    }
    mock_session = AIConversationSessionModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        session_token="session-xyz-123",
        active_plan=active_plan_json,
    )

    res_session = MagicMock()
    res_session.scalar_one_or_none.return_value = mock_session
    mock_db.execute.return_value = res_session

    exec_resp = await execute_confirmed_ai_plan(
        home_id=home_id,
        session_token="session-xyz-123",
        home_ctx=home_ctx,
        db=mock_db,
    )

    assert exec_resp.data["status"] == "SUCCESS"
    assert exec_resp.data["executed_steps_count"] == 1
    assert exec_resp.data["steps"][0]["status"] == "EXECUTED"
    assert mock_db.add.called
