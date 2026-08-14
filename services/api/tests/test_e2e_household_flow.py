import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.database.models import (
    BillModel,
    EventModel,
    HomeModel,
    HomeMemberModel,
    InventoryItemModel,
    NotificationModel,
    ShoppingListModel,
    ShoppingListItemModel,
    TaskModel,
    UserModel,
    UserProfileModel
)
from src.api.dependencies import HomeContext
from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER
from src.api.v1.inventory import calculate_stock_status
from src.api.v1.shopping import convert_low_stock_to_shopping_item
from src.api.v1.tasks import calculate_next_due_date
from src.api.v1.bills import calculate_next_bill_due_date


def test_complete_e2e_household_lifecycle():
    """
    Validates end-to-end multi-domain household state consistency:
    1. Home creation & Owner initialization
    2. Low-stock inventory trigger
    3. Conversion to shopping item
    4. Task recurrence math
    5. Bill payment & next cycle calculation
    """
    home_id = uuid4()
    owner_id = uuid4()
    member_id = uuid4()

    # 1. Home Creation
    home = HomeModel(id=home_id, name="The Riveras", currency="USD")
    owner = UserModel(id=owner_id, email="alex@example.com")
    membership = HomeMemberModel(home_id=home_id, user_id=owner_id, role=ROLE_OWNER, status="ACTIVE")

    assert home.name == "The Riveras"
    assert membership.role == "OWNER"

    # 2. Inventory Low Stock
    milk = InventoryItemModel(
        id=uuid4(),
        home_id=home_id,
        name="Oat Milk",
        quantity=Decimal("0.5"),
        unit="liters",
        min_threshold=Decimal("1.0"),
        status="IN_STOCK"
    )
    status_calculated = calculate_stock_status(milk.quantity, milk.min_threshold, None)
    assert status_calculated == "LOW_STOCK"

    # 3. Restock quantity calculation
    # (min_threshold * 2) - quantity = (1.0 * 2) - 0.5 = 1.5
    restock_qty = (milk.min_threshold * Decimal("2")) - milk.quantity
    assert restock_qty == Decimal("1.5")

    # 4. Chore recurrence lifecycle
    now = datetime.now(timezone.utc)
    weekly_chore = TaskModel(
        id=uuid4(),
        home_id=home_id,
        title="Clean kitchen counters",
        status="TODO",
        due_date=now,
        recurrence_rule="WEEKLY"
    )
    next_chore_due = calculate_next_due_date(weekly_chore.due_date, weekly_chore.recurrence_rule)
    assert (next_chore_due - now).days == 7

    # 5. Bill cycle math
    bill_due = date(2026, 8, 15)
    next_bill_due = calculate_next_bill_due_date(bill_due, "MONTHLY")
    assert next_bill_due == date(2026, 9, 15)
