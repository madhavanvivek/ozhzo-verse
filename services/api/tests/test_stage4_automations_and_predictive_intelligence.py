import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.automations import (
    create_automation,
    disable_automation,
    dismiss_recommendation,
    enable_automation,
    get_household_intelligence_dashboard,
    list_automations,
    propose_ai_automation,
    run_automation_manually,
    update_automation
)
from src.infrastructure.database.models import (
    AutomationExecutionModel,
    AutomationModel,
    BillModel,
    HomeModel,
    HouseholdRecommendationModel,
    InventoryItemModel,
    TaskModel,
    UserModel
)
from src.schemas.automations import (
    ActionType,
    AIAutomationProposalRequest,
    AutomationActionSchema,
    AutomationCreateRequest,
    AutomationStatus,
    AutomationUpdateRequest,
    ConditionGroupSchema,
    ConditionOperator,
    ConditionRuleSchema,
    TriggerType,
)
from src.services.automation_condition_engine import AutomationConditionEngine
from src.services.automation_engine import automation_engine


# ==============================================================================
# 1. DETERMINISTIC CONDITION ENGINE TESTS
# ==============================================================================

def test_condition_engine_numeric_and_equality_evaluation():
    """
    Verifies that the condition engine evaluates numeric and string comparisons accurately.
    """
    group = ConditionGroupSchema(
        operator="AND",
        rules=[
            ConditionRuleSchema(field="quantity", op=ConditionOperator.LESS_THAN, value=2.0),
            ConditionRuleSchema(field="item_type", op=ConditionOperator.EQUALS, value="CONSUMABLE")
        ]
    )

    # Should match
    payload_match = {"quantity": "1.500", "item_type": "CONSUMABLE"}
    assert AutomationConditionEngine.evaluate_group(group, payload_match) is True

    # Should fail numeric condition
    payload_high = {"quantity": 5.0, "item_type": "CONSUMABLE"}
    assert AutomationConditionEngine.evaluate_group(group, payload_high) is False

    # Should fail string condition
    payload_wrong_type = {"quantity": 1.0, "item_type": "DURABLE"}
    assert AutomationConditionEngine.evaluate_group(group, payload_wrong_type) is False


def test_condition_engine_or_logic_and_contains():
    """
    Verifies OR operator logic and string substring matching.
    """
    group = ConditionGroupSchema(
        operator="OR",
        rules=[
            ConditionRuleSchema(field="title", op=ConditionOperator.CONTAINS, value="Electric"),
            ConditionRuleSchema(field="priority", op=ConditionOperator.EQUALS, value="HIGH")
        ]
    )

    assert AutomationConditionEngine.evaluate_group(group, {"title": "Electricity Bill", "priority": "NORMAL"}) is True
    assert AutomationConditionEngine.evaluate_group(group, {"title": "Plumbing", "priority": "HIGH"}) is True
    assert AutomationConditionEngine.evaluate_group(group, {"title": "Water", "priority": "LOW"}) is False


# ==============================================================================
# 2. AUTOMATION CRUD & CONTROLS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_and_manage_automation_lifecycle():
    """
    Verifies creating, enabling, disabling, and updating an automation rule.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    req = AutomationCreateRequest(
        name="Auto Restock Milk",
        description="Add milk to shopping when low",
        trigger_type=TriggerType.INVENTORY_LOW,
        conditions=ConditionGroupSchema(
            operator="AND",
            rules=[ConditionRuleSchema(field="quantity", op=ConditionOperator.LESS_THAN, value=2.0)]
        ),
        actions=[
            AutomationActionSchema(
                action_type=ActionType.ADD_SHOPPING_ITEM,
                params={"name": "Milk", "quantity": 1.0, "unit": "bottle"}
            )
        ]
    )

    created_resp = await create_automation(home_id=home_id, request=req, home_ctx=home_ctx, db=mock_db)
    assert created_resp.data.name == "Auto Restock Milk"
    assert created_resp.data.trigger_type == TriggerType.INVENTORY_LOW
    assert created_resp.data.status == AutomationStatus.ACTIVE
    assert mock_db.add.called
    assert mock_db.commit.called


# ==============================================================================
# 3. LOOP PROTECTION & IDEMPOTENCY
# ==============================================================================

@pytest.mark.asyncio
async def test_automation_loop_protection_guard():
    """
    Verifies that automation execution stops and records SKIPPED when recursion depth >= 3.
    """
    home_id = uuid4()
    auto = AutomationModel(
        id=uuid4(),
        home_id=home_id,
        name="Recursive Auto",
        trigger_type="TASK_COMPLETED",
        conditions={},
        actions=[{"action_type": "CREATE_TASK", "params": {"title": "Loop Task"}}],
        status="ACTIVE"
    )

    mock_db = AsyncMock()

    exec_result = await automation_engine.execute_single_automation(
        db=mock_db,
        automation=auto,
        event_payload={"id": "evt-1"},
        depth=3  # At limit
    )

    assert exec_result.status == "SKIPPED"
    assert "Loop protection triggered" in (exec_result.error_details or "")


@pytest.mark.asyncio
async def test_automation_idempotency_duplicate_suppression():
    """
    Verifies that identical events do not trigger duplicate action executions.
    """
    home_id = uuid4()
    auto_id = uuid4()
    auto = AutomationModel(
        id=auto_id,
        home_id=home_id,
        name="Idempotent Restock",
        trigger_type="INVENTORY_LOW",
        conditions={},
        actions=[{"action_type": "ADD_SHOPPING_ITEM", "params": {"name": "Eggs"}}],
        status="ACTIVE"
    )

    mock_db = AsyncMock()

    # Mock that existing execution record is found
    existing_exec = AutomationExecutionModel(
        id=uuid4(),
        automation_id=auto_id,
        home_id=home_id,
        status="SUCCESS",
        idempotency_key="mock-idemp-key"
    )
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = existing_exec
    mock_db.execute.return_value = res_mock

    result = await automation_engine.execute_single_automation(
        db=mock_db,
        automation=auto,
        event_payload={"id": "inv-item-123"}
    )

    assert result == existing_exec


# ==============================================================================
# 4. PREDICTIVE INTELLIGENCE & RECOMMENDATIONS DASHBOARD
# ==============================================================================

@pytest.mark.asyncio
async def test_household_intelligence_dashboard_and_recommendations():
    """
    Verifies aggregation of active automations, executions, and predictive recommendations.
    """
    home_id = uuid4()
    mock_user = UserModel(id=uuid4(), email="admin@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Sunset Hill")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # Home
    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home

    # Automations
    res_autos = MagicMock()
    res_autos.scalars.return_value.all.return_value = []

    # Executions
    res_execs = MagicMock()
    res_execs.scalars.return_value.all.return_value = []

    # Low stock
    mock_low_stock = [
        InventoryItemModel(
            id=uuid4(),
            home_id=home_id,
            name="Olive Oil",
            item_type="CONSUMABLE",
            quantity=Decimal("0.500"),
            min_threshold=Decimal("1.000"),
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
        res_autos,
        res_execs,
        res_inv,    # Low stock
        empty_res,  # Bills
        empty_res   # Overdue Tasks
    ]

    dash_resp = await get_household_intelligence_dashboard(home_id=home_id, home_ctx=home_ctx, db=mock_db)
    assert dash_resp.data.home_name == "Sunset Hill"
    assert len(dash_resp.data.recommendations) >= 1
    assert any(r.domain == "INVENTORY" for r in dash_resp.data.recommendations)
    assert len(dash_resp.data.predicted_patterns) >= 1


# ==============================================================================
# 5. AI AUTOMATION PROPOSAL ASSISTANCE
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_automation_proposal_generation():
    """
    Verifies that AI converts natural language prompts into validated structured proposals.
    """
    mock_user = UserModel(id=uuid4(), email="user@ozhzo.com")
    home_ctx = HomeContext(home_id=uuid4(), user=mock_user, role="OWNER")

    req = AIAutomationProposalRequest(
        prompt="Whenever milk runs low in the pantry, add it to the shopping list"
    )
    proposal_resp = await propose_ai_automation(home_id=home_ctx.home_id, request=req, home_ctx=home_ctx)

    assert proposal_resp.data.trigger_type == TriggerType.INVENTORY_LOW
    assert "Milk" in proposal_resp.data.name or "Auto-Restock" in proposal_resp.data.name
    assert len(proposal_resp.data.actions) >= 1
    assert proposal_resp.data.actions[0].action_type == ActionType.ADD_SHOPPING_ITEM
    assert proposal_resp.data.requires_confirmation is True

