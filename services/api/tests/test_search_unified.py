import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.database.models import (
    BillModel,
    EventModel,
    InventoryItemModel,
    ShoppingListItemModel,
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

    inv_item = InventoryItemModel(id=uuid4(), home_id=home_id, name="Olive Oil", quantity=Decimal("1.0"), unit="bottle", status="IN_STOCK")
    shop_item = ShoppingListItemModel(id=uuid4(), home_id=home_id, name="Olive Oil Spray", quantity=Decimal("1.0"), unit="can", priority="MEDIUM", is_checked=False)
    task_item = TaskModel(id=uuid4(), home_id=home_id, title="Refill olive oil cruet", status="TODO", priority="LOW")
    event_item = EventModel(id=uuid4(), home_id=home_id, title="Olive harvest cooking class", start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))
    bill_item = BillModel(id=uuid4(), home_id=home_id, title="Olive Grove Market Subscription", category="Utilities", amount=Decimal("25.00"), currency="USD", due_date=date(2026, 8, 30), status="UNPAID")

    # Mock DB executions for 5 domain queries
    res1 = MagicMock(); res1.scalars.return_value.all.return_value = [inv_item]
    res2 = MagicMock(); res2.scalars.return_value.all.return_value = [shop_item]
    res3 = MagicMock(); res3.scalars.return_value.all.return_value = [task_item]
    res4 = MagicMock(); res4.scalars.return_value.all.return_value = [event_item]
    res5 = MagicMock(); res5.scalars.return_value.all.return_value = [bill_item]
    mock_db.execute.side_effect = [res1, res2, res3, res4, res5]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await unified_home_search(q="Olive", limit_per_domain=5, home_ctx=ctx, db=mock_db)

    assert res.success is True
    data = res.data
    assert data.total_results == 5
    assert data.results_by_domain["INVENTORY"] == 1
    assert data.results_by_domain["SHOPPING"] == 1
    assert data.results_by_domain["TASK"] == 1
    assert data.results_by_domain["EVENT"] == 1
    assert data.results_by_domain["BILL"] == 1


@pytest.mark.asyncio
async def test_unified_search_rbac_conceals_bills_for_child():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    inv_item = InventoryItemModel(id=uuid4(), home_id=home_id, name="Apple Juice", quantity=Decimal("2.0"), unit="bottles", status="IN_STOCK")
    shop_item = ShoppingListItemModel(id=uuid4(), home_id=home_id, name="Apples (Honeycrisp)", quantity=Decimal("6.0"), unit="pcs", priority="LOW", is_checked=False)
    task_item = TaskModel(id=uuid4(), home_id=home_id, title="Pack apples for school lunch", status="TODO", priority="MEDIUM")
    event_item = EventModel(id=uuid4(), home_id=home_id, title="Apple Orchard Trip", start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))

    # Child only queries 4 domains (bills domain query is skipped entirely)
    res1 = MagicMock(); res1.scalars.return_value.all.return_value = [inv_item]
    res2 = MagicMock(); res2.scalars.return_value.all.return_value = [shop_item]
    res3 = MagicMock(); res3.scalars.return_value.all.return_value = [task_item]
    res4 = MagicMock(); res4.scalars.return_value.all.return_value = [event_item]
    mock_db.execute.side_effect = [res1, res2, res3, res4]

    user = UserModel(id=user_id, email="leo@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_CHILD)

    res = await unified_home_search(q="Apple", limit_per_domain=5, home_ctx=ctx, db=mock_db)

    assert res.success is True
    data = res.data
    assert data.results_by_domain["BILL"] == 0
    domains = [item.domain for item in data.items]
    assert "BILL" not in domains
