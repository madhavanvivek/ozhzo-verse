import pytest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.shopping import (
    CheckItemRequest,
    ConvertFromInventoryRequest,
    CreateShoppingItemRequest,
    CreateShoppingListRequest
)
from src.api.v1.shopping import (
    create_shopping_list,
    add_shopping_item,
    toggle_item_checked,
    remove_shopping_item,
    convert_low_stock_to_shopping_item
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import (
    InventoryItemModel,
    ShoppingListModel,
    ShoppingListItemModel,
    UserModel
)


@pytest.mark.asyncio
async def test_create_shopping_list_and_add_item():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    list_id = uuid4()

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    req = CreateShoppingItemRequest(
        name="Organic Sourdough Bread",
        quantity=Decimal("2.0"),
        unit="loaves",
        priority="HIGH"
    )

    mock_redis = AsyncMock()
    res = await add_shopping_item(list_id, req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.name == "Organic Sourdough Bread"
    assert res.data.quantity == Decimal("2.0")
    assert res.data.priority == "HIGH"
    assert res.data.is_checked is False
    assert res.data.version == 1
    assert mock_db.add.call_count >= 1


@pytest.mark.asyncio
async def test_toggle_item_checked_optimistic_concurrency():
    mock_db = AsyncMock()
    home_id = uuid4()
    item_id = uuid4()
    item = ShoppingListItemModel(
        id=item_id,
        home_id=home_id,
        name="Milk",
        is_checked=False,
        version=1
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = item
    mock_db.execute.return_value = mock_res

    user = UserModel(id=uuid4(), email="sarah@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_MEMBER)
    mock_redis = AsyncMock()

    # 1. Normal toggle check (version 1 -> 2)
    req = CheckItemRequest(is_checked=True, version=1)
    res = await toggle_item_checked(item_id, req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert item.is_checked is True
    assert item.version == 2

    # 2. Stale version conflict test (client sends version 1 when server is version 2)
    stale_req = CheckItemRequest(is_checked=False, version=1)
    with pytest.raises(HTTPException) as exc_info:
        await toggle_item_checked(item_id, stale_req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_convert_low_stock_inventory_to_shopping_item():
    mock_db = AsyncMock()
    home_id = uuid4()
    inv_id = uuid4()
    list_id = uuid4()

    inv_item = InventoryItemModel(
        id=inv_id,
        home_id=home_id,
        name="Olive Oil",
        quantity=Decimal("0.5"),
        unit="bottles",
        min_threshold=Decimal("2.0"),
        status="LOW_STOCK",
        deleted_at=None
    )
    shopping_list = ShoppingListModel(id=list_id, home_id=home_id, name="Main Shopping List")

    mock_res1 = MagicMock()
    mock_res1.scalar_one_or_none.return_value = inv_item
    mock_res2 = MagicMock()
    mock_res2.scalar_one_or_none.return_value = shopping_list

    mock_db.execute.side_effect = [mock_res1, mock_res2]

    user = UserModel(id=uuid4(), email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_redis = AsyncMock()

    res = await convert_low_stock_to_shopping_item(
        inv_id,
        payload=ConvertFromInventoryRequest(),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert res.success is True
    assert res.data.name == "Olive Oil"
    # min_threshold * 2 - quantity = 4.0 - 0.5 = 3.5
    assert res.data.quantity == Decimal("3.5")
    assert res.data.priority == "HIGH"


def test_shopping_rbac_permissions():
    # Child & Guest can check/uncheck shopping items in store
    assert has_permission(ROLE_CHILD, "shopping:check") is True
    assert has_permission(ROLE_GUEST, "shopping:check") is True

    # Child and Member can view and add items
    assert has_permission(ROLE_MEMBER, "shopping:create") is True
    assert has_permission(ROLE_CHILD, "shopping:view") is True

    # Guest cannot delete lists
    assert has_permission(ROLE_GUEST, "shopping:delete") is False
