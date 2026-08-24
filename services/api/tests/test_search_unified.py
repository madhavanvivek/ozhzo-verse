import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.database.models import (
    BillModel,
    EventModel,
    InventoryItemModel,
    PurchaseItemModel,
    TaskModel,
    UserModel
)
from src.api.v1.search import unified_home_search
from src.api.dependencies import HomeContext
from src.domain.permissions import ROLE_OWNER, ROLE_CHILD, ROLE_GUEST


@pytest.mark.asyncio
async def test_unified_search_across_all_domains_owner():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    inv_item = InventoryItemModel(id=uuid4(), home_id=home_id, item_type="CONSUMABLE", name="Olive Oil", quantity=Decimal("1.0"), unit="bottle", status="IN_STOCK")
    shop_item = PurchaseItemModel(id=uuid4(), home_id=home_id, name="Olive Oil Spray", quantity=Decimal("1.0"), unit="can", status="PENDING")
    task_item = TaskModel(id=uuid4(), home_id=home_id, title="Refill olive oil cruet", status="TODO", priority="LOW")
    event_item = EventModel(id=uuid4(), home_id=home_id, title="Olive harvest cooking class", start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))
    bill_item = BillModel(id=uuid4(), home_id=home_id, title="Olive Grove Market Subscription", expected_amount=Decimal("25.00"), currency="USD", due_date=date(2026, 8, 30), status="UNPAID")

    # Mock DB executions for 8 domain queries (ASSET, INVENTORY, LOCATION, PURCHASE, TASK, BILL, EVENT, MEMBER)
    res_asset = MagicMock(); res_asset.scalars.return_value.all.return_value = []
    res_inv = MagicMock(); res_inv.scalars.return_value.all.return_value = [inv_item]
    res_loc = MagicMock(); res_loc.scalars.return_value.all.return_value = []
    res_purchase = MagicMock(); res_purchase.scalars.return_value.all.return_value = [shop_item]
    res_task = MagicMock(); res_task.scalars.return_value.all.return_value = [task_item]
    res_bill = MagicMock(); res_bill.scalars.return_value.all.return_value = [bill_item]
    res_event = MagicMock(); res_event.scalars.return_value.all.return_value = [event_item]
    res_member = MagicMock(); res_member.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [res_asset, res_inv, res_loc, res_purchase, res_task, res_bill, res_event, res_member]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await unified_home_search(q="Olive", limit_per_domain=5, home_ctx=ctx, db=mock_db)

    assert res.success is True
    data = res.data
    assert data.total_results == 5
    assert data.results_by_domain["INVENTORY"] == 1
    assert data.results_by_domain["PURCHASE"] == 1
    assert data.results_by_domain["TASK"] == 1
    assert data.results_by_domain["EVENT"] == 1
    assert data.results_by_domain["BILL"] == 1


@pytest.mark.asyncio
async def test_unified_search_rbac_conceals_bills_for_child():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    inv_item = InventoryItemModel(id=uuid4(), home_id=home_id, item_type="CONSUMABLE", name="Apple Juice", quantity=Decimal("2.0"), unit="bottles", status="IN_STOCK")
    shop_item = PurchaseItemModel(id=uuid4(), home_id=home_id, name="Apples (Honeycrisp)", quantity=Decimal("6.0"), unit="pcs", status="PENDING")
    task_item = TaskModel(id=uuid4(), home_id=home_id, title="Pack apples for school lunch", status="TODO", priority="MEDIUM")
    event_item = EventModel(id=uuid4(), home_id=home_id, title="Apple Orchard Trip", start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))

    # Child has no bills:view permission -> bill query is omitted (7 domain queries: ASSET, INVENTORY, LOCATION, PURCHASE, TASK, EVENT, MEMBER)
    res_asset = MagicMock(); res_asset.scalars.return_value.all.return_value = []
    res_inv = MagicMock(); res_inv.scalars.return_value.all.return_value = [inv_item]
    res_loc = MagicMock(); res_loc.scalars.return_value.all.return_value = []
    res_purchase = MagicMock(); res_purchase.scalars.return_value.all.return_value = [shop_item]
    res_task = MagicMock(); res_task.scalars.return_value.all.return_value = [task_item]
    res_event = MagicMock(); res_event.scalars.return_value.all.return_value = [event_item]
    res_member = MagicMock(); res_member.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [res_asset, res_inv, res_loc, res_purchase, res_task, res_event, res_member]

    user = UserModel(id=user_id, email="leo@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_CHILD)

    res = await unified_home_search(q="Apple", limit_per_domain=5, home_ctx=ctx, db=mock_db)

    assert res.success is True
    data = res.data
    assert data.results_by_domain["BILL"] == 0
    domains = [item.domain for item in data.items]
    assert "BILL" not in domains
