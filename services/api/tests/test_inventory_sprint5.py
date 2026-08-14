import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
from src.schemas.inventory import CreateInventoryItemRequest, UpdateInventoryItemRequest
from src.api.v1.inventory import (
    calculate_stock_status,
    create_inventory_item,
    update_inventory_item,
    delete_inventory_item,
    list_inventory_items
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import InventoryItemModel, UserModel


def test_calculate_stock_status():
    # 1. Normal stock
    assert calculate_stock_status(Decimal("5.0"), Decimal("2.0"), None) == "IN_STOCK"
    assert calculate_stock_status(Decimal("2.1"), Decimal("2.0"), None) == "IN_STOCK"

    # 2. Low stock (at or below threshold)
    assert calculate_stock_status(Decimal("2.0"), Decimal("2.0"), None) == "LOW_STOCK"
    assert calculate_stock_status(Decimal("0.5"), Decimal("2.0"), None) == "LOW_STOCK"

    # 3. Out of stock
    assert calculate_stock_status(Decimal("0.0"), Decimal("2.0"), None) == "OUT_OF_STOCK"
    assert calculate_stock_status(Decimal("0"), Decimal("0"), None) == "OUT_OF_STOCK"

    # 4. Expired
    past_date = date.today() - timedelta(days=2)
    assert calculate_stock_status(Decimal("5.0"), Decimal("2.0"), past_date) == "EXPIRED"


@pytest.mark.asyncio
async def test_create_inventory_item_low_stock_notification():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    # Mock member query for notification
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [user_id]
    mock_db.execute.return_value = mock_res
    mock_db.get.return_value = None

    req = CreateInventoryItemRequest(
        name="Almond Milk",
        quantity=Decimal("0.5"),
        unit="liters",
        min_threshold=Decimal("1.0"),
        location="Fridge Top Shelf"
    )

    mock_redis = AsyncMock()
    res = await create_inventory_item(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.name == "Almond Milk"
    assert res.data.status == "LOW_STOCK"
    # Added inventory item AND notification record
    assert mock_db.add.call_count >= 2


@pytest.mark.asyncio
async def test_update_inventory_item():
    mock_db = AsyncMock()
    home_id = uuid4()
    item_id = uuid4()
    user_id = uuid4()

    item = InventoryItemModel(
        id=item_id,
        home_id=home_id,
        name="Olive Oil",
        quantity=Decimal("2.0"),
        unit="bottles",
        min_threshold=Decimal("1.0"),
        status="IN_STOCK"
    )

    mock_res1 = MagicMock()
    mock_res1.scalar_one_or_none.return_value = item
    mock_res2 = MagicMock()
    mock_res2.scalars.return_value.all.return_value = [user_id]
    mock_db.execute.side_effect = [mock_res1, mock_res2]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    req = UpdateInventoryItemRequest(quantity=Decimal("0.5"))
    mock_redis = AsyncMock()

    res = await update_inventory_item(item_id, req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert item.status == "LOW_STOCK"
    assert item.quantity == Decimal("0.5")


@pytest.mark.asyncio
async def test_delete_inventory_item():
    mock_db = AsyncMock()
    home_id = uuid4()
    item_id = uuid4()

    item = InventoryItemModel(id=item_id, home_id=home_id, name="Old Flour", deleted_at=None)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = item
    mock_db.execute.return_value = mock_res

    user = UserModel(id=uuid4(), email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_redis = AsyncMock()

    res = await delete_inventory_item(item_id, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert item.deleted_at is not None


def test_inventory_rbac_permissions():
    assert has_permission(ROLE_OWNER, "inventory:create") is True
    assert has_permission(ROLE_OWNER, "inventory:delete") is True
    assert has_permission(ROLE_ADMIN, "inventory:edit") is True
    assert has_permission(ROLE_MEMBER, "inventory:edit") is True
    assert has_permission(ROLE_CHILD, "inventory:create") is False
    assert has_permission(ROLE_CHILD, "inventory:delete") is False
    assert has_permission(ROLE_GUEST, "inventory:edit") is False
    assert has_permission(ROLE_GUEST, "inventory:view") is True
