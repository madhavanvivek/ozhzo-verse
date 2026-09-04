import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.search import unified_home_search
from src.infrastructure.database.models import (
    BillModel,
    EventModel,
    HomeMemberModel,
    HomeModel,
    InventoryItemModel,
    LocationModel,
    PurchaseItemModel,
    TaskModel,
    UserModel,
    UserProfileModel
)
from src.schemas.search import UnifiedSearchResponse


# ==============================================================================
# 1. UNIFIED SEARCH ACROSS ALL MODULES WITH HOME CONTEXT ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_unified_search_all_domains_in_current_home():
    """
    Verifies that unified search queries across Tasks, Bills, Calendar, Shopping, Inventory, and Members
    returning properly structured results with deep links.
    """
    home_id = uuid4()
    user_id = uuid4()

    mock_user = UserModel(id=user_id, email="search_tester@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Sunset Haven", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # Domain mock data
    now = datetime.now(timezone.utc)
    mock_assets = [
        InventoryItemModel(
            id=uuid4(),
            home_id=home_id,
            name="Power Drill",
            item_type="ASSET",
            location_path="Garage > Tool Cabinet",
            asset_status="AVAILABLE",
            condition="Good"
        )
    ]
    mock_consumables = [
        InventoryItemModel(
            id=uuid4(),
            home_id=home_id,
            name="Drill Bits Pack",
            item_type="CONSUMABLE",
            quantity=Decimal("10.000"),
            unit="pcs",
            status="GOOD"
        )
    ]
    mock_locations = [
        LocationModel(
            id=uuid4(),
            home_id=home_id,
            name="Tool Cabinet",
            location_type="CABINET"
        )
    ]
    mock_purchases = [
        PurchaseItemModel(
            id=uuid4(),
            home_id=home_id,
            name="Drill Lubricant Oil",
            quantity=Decimal("1.000"),
            unit="can",
            status="PENDING"
        )
    ]
    mock_tasks = [
        TaskModel(
            id=uuid4(),
            home_id=home_id,
            title="Fix Drill Mount",
            priority="HIGH",
            status="TODO",
            due_date=now + timedelta(days=1)
        )
    ]
    mock_bills = [
        BillModel(
            id=uuid4(),
            home_id=home_id,
            title="Drill Maintenance Invoice",
            expected_amount=Decimal("450.00"),
            currency="INR",
            due_date=date.today(),
            status="UNPAID"
        )
    ]
    mock_events = [
        EventModel(
            id=uuid4(),
            home_id=home_id,
            title="Drill Repair Workshop",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=2),
            status="CONFIRMED"
        )
    ]
    mock_members = [
        HomeMemberModel(
            id=uuid4(),
            home_id=home_id,
            user_id=user_id,
            role="OWNER",
            status="ACTIVE",
            user=UserModel(
                id=user_id,
                email="drillmaster@ozhzo.com",
                profile=UserProfileModel(user_id=user_id, display_name="Drill Master")
            )
        )
    ]

    # Setup mock executes
    res_assets = MagicMock()
    res_assets.scalars.return_value.all.return_value = mock_assets

    res_inv = MagicMock()
    res_inv.scalars.return_value.all.return_value = mock_consumables

    res_loc = MagicMock()
    res_loc.scalars.return_value.all.return_value = mock_locations

    res_purch = MagicMock()
    res_purch.scalars.return_value.all.return_value = mock_purchases

    res_task = MagicMock()
    res_task.scalars.return_value.all.return_value = mock_tasks

    res_bill = MagicMock()
    res_bill.scalars.return_value.all.return_value = mock_bills

    res_evt = MagicMock()
    res_evt.scalars.return_value.all.return_value = mock_events

    res_mem = MagicMock()
    res_mem.scalars.return_value.all.return_value = mock_members

    mock_db.execute.side_effect = [
        res_assets,
        res_inv,
        res_loc,
        res_purch,
        res_task,
        res_bill,
        res_evt,
        res_mem
    ]

    res = await unified_home_search(
        q="drill",
        domain=None,
        limit_per_domain=5,
        home_ctx=home_ctx,
        db=mock_db
    )

    assert res.data.query == "drill"
    assert res.data.total_results == 8

    domains_found = set(item.domain for item in res.data.items)
    assert domains_found == {"ASSET", "INVENTORY", "LOCATION", "PURCHASE", "TASK", "BILL", "EVENT", "MEMBER"}

    # Verify deep links
    for item in res.data.items:
        assert item.navigation_target.startswith("/")


@pytest.mark.asyncio
async def test_search_role_based_bill_protection():
    """
    Verifies that CHILD and GUEST roles cannot view Bills in search results.
    """
    home_id = uuid4()
    child_id = uuid4()

    mock_child = UserModel(id=child_id, email="child@ozhzo.com")
    home_ctx = HomeContext(home_id=home_id, user=mock_child, role="CHILD")

    mock_db = AsyncMock()

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    # Child search should bypass Bill query completely
    mock_db.execute.side_effect = [
        empty_res, # ASSET
        empty_res, # INVENTORY
        empty_res, # LOCATION
        empty_res, # PURCHASE
        empty_res, # TASK
        # (BILL IS SKIPPED)
        empty_res, # EVENT
        empty_res  # MEMBER
    ]

    res = await unified_home_search(
        q="electricity",
        domain=None,
        limit_per_domain=5,
        home_ctx=home_ctx,
        db=mock_db
    )

    assert res.data.results_by_domain["BILL"] == 0
    assert not any(item.domain == "BILL" for item in res.data.items)


@pytest.mark.asyncio
async def test_search_domain_filtering():
    """
    Verifies that passing a specific domain parameter (e.g. TASK) queries only that domain.
    """
    home_id = uuid4()
    user_id = uuid4()

    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    task_res = MagicMock()
    task_res.scalars.return_value.all.return_value = [
        TaskModel(
            id=uuid4(),
            home_id=home_id,
            title="Clean Microwave",
            priority="NORMAL",
            status="TODO"
        )
    ]
    mock_db.execute.return_value = task_res

    res = await unified_home_search(
        q="microwave",
        domain="TASK",
        limit_per_domain=5,
        home_ctx=home_ctx,
        db=mock_db
    )

    assert res.data.total_results == 1
    assert res.data.items[0].domain == "TASK"
    assert res.data.items[0].title == "Clean Microwave"
    assert res.data.items[0].navigation_target == "/tasks"
