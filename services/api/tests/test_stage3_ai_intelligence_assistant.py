import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.ai import (
    ai_chat_interaction,
    confirm_ai_action,
    get_ai_recommendations,
    get_ai_usage_metrics,
    reject_ai_action
)
from src.infrastructure.database.models import (
    AuditLogModel,
    BillModel,
    EventModel,
    HomeMemberModel,
    HomeModel,
    InventoryItemModel,
    PurchaseItemModel,
    TaskModel,
    UserModel,
    UserProfileModel
)
from src.schemas.ai import (
    AIActionType,
    AIChatRequest,
    AIIntentType,
)
from src.services.ai_assistant_service import ai_assistant_service


# ==============================================================================
# 1. NATURAL LANGUAGE INTENT DETECTION & CONTEXTUAL REPLIES
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_chat_query_tasks_contextual_response():
    """
    Verifies that asking about tasks returns active chores from the current home context.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Emerald Villa", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # Mocks for context builder
    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home

    mock_tasks = [
        TaskModel(
            id=uuid4(),
            home_id=home_id,
            title="Clean solar panels",
            priority="HIGH",
            status="TODO",
            due_date=date.today()
        )
    ]
    res_tasks = MagicMock()
    res_tasks.scalars.return_value.all.return_value = mock_tasks

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_home,   # Home metadata
        res_tasks,  # Tasks
        empty_res,  # Bills
        empty_res,  # Events
        empty_res,  # Inventory
        empty_res,  # Shopping
        empty_res   # Members
    ]

    req = AIChatRequest(message="What do I need to do today?")
    resp = await ai_chat_interaction(home_id=home_id, request=req, home_ctx=home_ctx, db=mock_db)

    assert resp.data.detected_intent == AIIntentType.QUERY_TASKS
    assert "Clean solar panels" in resp.data.message
    assert "Emerald Villa" in resp.data.message
    assert resp.data.action_proposal is None


# ==============================================================================
# 2. WRITE ACTION PROPOSAL & AUTHORITATIVE CONFIRMATION LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_shopping_action_proposal_and_execution_lifecycle():
    """
    Verifies full lifecycle:
    1. User says 'Add Almond Milk to shopping' -> AI generates ADD_SHOPPING_ITEM Action Proposal.
    2. User confirms action -> Authoritative PurchaseItemModel created, Audit logged.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="chef@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Sunset Haven", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_home,
        empty_res,
        empty_res,
        empty_res,
        empty_res,
        empty_res,
        empty_res
    ]

    # Step 1: Propose Action
    req = AIChatRequest(message="Add Almond Milk to shopping list")
    chat_resp = await ai_chat_interaction(home_id=home_id, request=req, home_ctx=home_ctx, db=mock_db)

    assert chat_resp.data.detected_intent == AIIntentType.ADD_SHOPPING_ITEM
    assert chat_resp.data.action_proposal is not None
    proposal = chat_resp.data.action_proposal
    assert proposal.action_type == AIActionType.ADD_SHOPPING_ITEM
    assert "Almond Milk" in proposal.title
    assert proposal.requires_confirmation is True

    # Step 2: Confirm and Authoritatively Execute
    confirm_resp = await confirm_ai_action(
        home_id=home_id,
        action_id=proposal.id,
        home_ctx=home_ctx,
        db=mock_db
    )

    assert confirm_resp.data.success is True
    assert confirm_resp.data.action_type == AIActionType.ADD_SHOPPING_ITEM
    assert "Almond Milk" in confirm_resp.data.message
    # Assert DB additions occurred
    assert mock_db.add.call_count >= 2 # PurchaseItemModel + AuditLogModel
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_ai_task_action_proposal_and_execution():
    """
    Verifies that 'Create task Water garden plants tomorrow' creates a staged task proposal
    which executes upon confirmation.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="gardener@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Green Estate", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="ADMIN")

    mock_db = AsyncMock()

    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_home,
        empty_res,
        empty_res,
        empty_res,
        empty_res,
        empty_res,
        empty_res
    ]

    # Propose
    req = AIChatRequest(message="Create task Water garden plants tomorrow")
    chat_resp = await ai_chat_interaction(home_id=home_id, request=req, home_ctx=home_ctx, db=mock_db)

    assert chat_resp.data.detected_intent == AIIntentType.CREATE_TASK
    proposal = chat_resp.data.action_proposal
    assert proposal is not None
    assert proposal.action_type == AIActionType.CREATE_TASK
    assert "Water Garden Plants" in proposal.title or "Water garden plants" in proposal.title

    # Execute
    exec_resp = await confirm_ai_action(
        home_id=home_id,
        action_id=proposal.id,
        home_ctx=home_ctx,
        db=mock_db
    )

    assert exec_resp.data.success is True
    assert exec_resp.data.action_type == AIActionType.CREATE_TASK


# ==============================================================================
# 3. ROLE & PERMISSION GUARD (CHILD / GUEST PROTECTION)
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_role_permission_guard_blocks_unauthorized_write():
    """
    Verifies that a CHILD role cannot create bills or execute financial commands.
    """
    home_id = uuid4()
    child_id = uuid4()
    mock_child = UserModel(id=child_id, email="kiddo@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Family Nest", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_child, role="CHILD")

    mock_db = AsyncMock()
    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_home,
        empty_res,
        # (Bills skipped for child)
        empty_res,
        empty_res,
        empty_res,
        empty_res
    ]

    req = AIChatRequest(message="Create bill Internet amount 1200")
    resp = await ai_chat_interaction(home_id=home_id, request=req, home_ctx=home_ctx, db=mock_db)

    # Permission denied politely in response
    assert "cannot create bills" in resp.data.message.lower() or "permission" in resp.data.message.lower()
    assert resp.data.action_proposal is None


# ==============================================================================
# 4. RECOMMENDATIONS & USAGE TRACKING
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_recommendations_and_usage_metrics():
    """
    Verifies proactive household recommendations and usage metric tracking.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="admin@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Lakeview Home", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home

    mock_low_stock = [
        InventoryItemModel(
            id=uuid4(),
            home_id=home_id,
            name="Olive Oil",
            item_type="CONSUMABLE",
            quantity=Decimal("0.500"),
            unit="bottle",
            status="LOW_STOCK"
        )
    ]
    res_inv = MagicMock()
    res_inv.scalars.return_value.all.return_value = mock_low_stock

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_home,
        empty_res,  # Tasks
        empty_res,  # Bills
        empty_res,  # Events
        res_inv,    # Low stock
        empty_res,  # Shopping
        empty_res   # Members
    ]

    recs_resp = await get_ai_recommendations(home_id=home_id, home_ctx=home_ctx, db=mock_db)
    assert len(recs_resp.data) >= 1
    assert any(r.domain == "INVENTORY" for r in recs_resp.data)

    # Check usage metrics
    usage_resp = await get_ai_usage_metrics(home_id=home_id, home_ctx=home_ctx)
    assert usage_resp.data.home_id == str(home_id)
    assert usage_resp.data.total_interactions >= 0
