import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.purchase_list import (
    CreatePurchaseItemRequest,
    PurchaseActionRequest,
    UpdatePurchaseItemRequest
)
from src.api.v1.purchase_list import (
    add_item_to_purchase_list,
    mark_item_as_purchased,
    restore_purchased_item,
    get_home_purchase_list,
    delete_purchase_item
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import (
    PurchaseItemModel,
    PurchaseHistoryModel,
    UserModel,
    UserProfileModel
)


@pytest.mark.asyncio
async def test_purchase_item_lifecycle_mark_and_restore():
    """
    Test complete purchase item lifecycle:
    1. Create item (status: PENDING)
    2. Mark as purchased (status: PURCHASED)
    3. Restore item (status: PENDING)
    4. Verify attributes (name, qty, unit, notes) preserved without duplicate item creation
    """
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="alex@example.com")
    user.profile = UserProfileModel(user_id=user_id, display_name="Alex Rivera")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    # 1. Create item
    item_id = uuid4()
    now = datetime.now(timezone.utc)
    item = PurchaseItemModel(
        id=item_id,
        home_id=home_id,
        name="Basmati Rice",
        quantity=Decimal("5.0"),
        unit="kg",
        notes="Extra long grain",
        status="PENDING",
        added_by=user_id,
        version=1,
        created_at=now,
        updated_at=now
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = item
    mock_db.execute.return_value = mock_res

    # 2. Mark as PURCHASED
    purchase_payload = PurchaseActionRequest(
        purchased_quantity=Decimal("5.0"),
        restock_inventory=False,
        notes="Bought from supermarket"
    )
    purchase_res = await mark_item_as_purchased(
        item_id=item_id,
        payload=purchase_payload,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert purchase_res.success is True
    assert purchase_res.data.status == "PURCHASED"
    assert item.status == "PURCHASED"
    assert item.purchased_by == user_id
    assert item.version == 2
    # Verify purchase history was added
    assert mock_db.add.call_count >= 1

    # 3. Restore to Shopping List
    restore_res = await restore_purchased_item(
        item_id=item_id,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert restore_res.success is True
    assert restore_res.data.status == "PENDING"
    assert restore_res.data.name == "Basmati Rice"
    assert restore_res.data.quantity == Decimal("5.0")
    assert restore_res.data.unit == "kg"
    assert restore_res.data.notes == "Extra long grain"
    assert restore_res.data.purchased_by is None
    assert restore_res.data.purchased_at is None
    assert item.status == "PENDING"
    assert item.purchased_by is None
    assert item.purchased_at is None
    assert item.version == 3


@pytest.mark.asyncio
async def test_restore_item_already_pending_rejected():
    """
    Restoring an already pending item must raise 400 Bad Request.
    """
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    item_id = uuid4()

    item = PurchaseItemModel(
        id=item_id,
        home_id=home_id,
        name="Olive Oil",
        quantity=Decimal("2.0"),
        unit="bottles",
        status="PENDING",
        added_by=user_id,
        version=1
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = item
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    with pytest.raises(HTTPException) as exc_info:
        await restore_purchased_item(
            item_id=item_id,
            home_ctx=ctx,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_cross_home_purchase_isolation():
    """
    Attempting to restore or access an item belonging to another home must return 404.
    """
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_a = uuid4()
    home_b = uuid4()
    user_id = uuid4()
    item_id = uuid4()

    # DB returns None when queried with home_b
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    ctx_b = HomeContext(home_id=home_b, user=user, role=ROLE_OWNER)

    with pytest.raises(HTTPException) as exc_info:
        await restore_purchased_item(
            item_id=item_id,
            home_ctx=ctx_b,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_info.value.status_code == 404


def test_shopping_list_permissions():
    """
    Verify RBAC for shopping list actions.
    """
    assert has_permission(ROLE_OWNER, "shopping:view") is True
    assert has_permission(ROLE_OWNER, "shopping:create") is True
    assert has_permission(ROLE_OWNER, "shopping:edit") is True
    assert has_permission(ROLE_OWNER, "shopping:check") is True
    assert has_permission(ROLE_OWNER, "shopping:delete") is True

    assert has_permission(ROLE_MEMBER, "shopping:view") is True
    assert has_permission(ROLE_MEMBER, "shopping:check") is True
    assert has_permission(ROLE_CHILD, "shopping:view") is True
    assert has_permission(ROLE_CHILD, "shopping:delete") is False
    assert has_permission(ROLE_GUEST, "shopping:delete") is False
