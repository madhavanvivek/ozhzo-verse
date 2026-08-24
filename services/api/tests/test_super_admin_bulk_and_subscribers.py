import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException
from src.api.v1.admin_users import bulk_user_action, hold_user, delete_user, reactivate_user
from src.api.v1.admin_homes import bulk_home_action, hold_home, archive_home, reactivate_home
from src.api.v1.admin_subscriptions import list_subscribers
from src.core.bootstrap import seed_demo_coupons
from src.infrastructure.database.models import (
    CouponModel,
    HomeModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
    UserProfileModel
)
from src.schemas.admin import (
    BulkUserActionRequest,
    BulkHomeActionRequest,
    HoldEntityRequest,
    DeleteEntityRequest,
    ReactivateEntityRequest
)


@pytest.mark.asyncio
async def test_bulk_user_action_activate_and_suspend():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    user_1 = UserModel(id=uuid4(), email="user1@example.com", is_active=True)
    user_2 = UserModel(id=uuid4(), email="user2@example.com", is_active=False)

    mock_db = AsyncMock()

    async def mock_get(model, uid):
        if uid == user_1.id:
            return user_1
        if uid == user_2.id:
            return user_2
        return None

    mock_db.get.side_effect = mock_get

    # 1. Bulk Suspend
    req_suspend = BulkUserActionRequest(
        user_ids=[user_1.id, user_2.id],
        action="SUSPEND",
        reason="Security review"
    )
    res_suspend = await bulk_user_action(req_suspend, super_admin=super_admin, db=mock_db)
    assert res_suspend.success is True
    assert res_suspend.data.total == 2
    assert len(res_suspend.data.succeeded) == 2
    assert user_1.is_active is False
    assert user_2.is_active is False

    # 2. Bulk Activate
    req_activate = BulkUserActionRequest(
        user_ids=[user_1.id, user_2.id],
        action="ACTIVATE",
        reason="Review cleared"
    )
    res_activate = await bulk_user_action(req_activate, super_admin=super_admin, db=mock_db)
    assert res_activate.success is True
    assert len(res_activate.data.succeeded) == 2
    assert user_1.is_active is True
    assert user_2.is_active is True


@pytest.mark.asyncio
async def test_bulk_user_action_protects_super_admin():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    other_user = UserModel(id=uuid4(), email="other@example.com", is_active=True)

    mock_db = AsyncMock()
    mock_db.get.side_effect = lambda model, uid: other_user if uid == other_user.id else super_admin

    req = BulkUserActionRequest(
        user_ids=[super_admin.id, other_user.id],
        action="SUSPEND",
        reason="Test suspend"
    )
    res = await bulk_user_action(req, super_admin=super_admin, db=mock_db)
    assert res.success is True
    assert len(res.data.succeeded) == 1
    assert len(res.data.failed) == 1
    assert res.data.failed[0]["user_id"] == str(super_admin.id)
    assert other_user.is_active is False


@pytest.mark.asyncio
async def test_bulk_home_action_states():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    home_1 = HomeModel(id=uuid4(), name="Home 1", status="ACTIVE")
    home_2 = HomeModel(id=uuid4(), name="Home 2", status="SUSPENDED")

    mock_db = AsyncMock()
    mock_db.get.side_effect = lambda model, hid: home_1 if hid == home_1.id else (home_2 if hid == home_2.id else None)

    # Bulk Hold
    req_hold = BulkHomeActionRequest(
        home_ids=[home_1.id, home_2.id],
        action="HOLD",
        reason="Billing dispute"
    )
    res_hold = await bulk_home_action(req_hold, super_admin=super_admin, db=mock_db)
    assert res_hold.success is True
    assert len(res_hold.data.succeeded) == 2
    assert home_1.status == "HELD"
    assert home_2.status == "HELD"

    # Bulk Activate
    req_act = BulkHomeActionRequest(
        home_ids=[home_1.id, home_2.id],
        action="ACTIVATE",
        reason="Dispute resolved"
    )
    res_act = await bulk_home_action(req_act, super_admin=super_admin, db=mock_db)
    assert res_act.success is True
    assert home_1.status == "ACTIVE"
    assert home_2.status == "ACTIVE"


@pytest.mark.asyncio
async def test_single_user_lifecycle_endpoints():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    user = UserModel(id=uuid4(), email="single@example.com", is_active=True)

    mock_db = AsyncMock()
    mock_db.get.return_value = user
    mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

    # Hold
    hold_res = await hold_user(user.id, HoldEntityRequest(reason="Compliance hold"), super_admin=super_admin, db=mock_db)
    assert hold_res.success is True
    assert user.is_active is False

    # Reactivate
    reactivate_res = await reactivate_user(user.id, ReactivateEntityRequest(reason="Compliance cleared"), super_admin=super_admin, db=mock_db)
    assert reactivate_res.success is True
    assert user.is_active is True

    # Safe Delete
    del_res = await delete_user(user.id, DeleteEntityRequest(reason="GDPR Erasure request"), super_admin=super_admin, db=mock_db)
    assert del_res.success is True
    assert user.is_active is False
    assert user.deleted_at is not None


@pytest.mark.asyncio
async def test_single_home_lifecycle_endpoints():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    home = HomeModel(id=uuid4(), name="Family Villa", status="ACTIVE")

    mock_db = AsyncMock()
    mock_db.get.return_value = home

    # Hold
    hold_res = await hold_home(home.id, HoldEntityRequest(reason="Under investigation"), super_admin=super_admin, db=mock_db)
    assert hold_res.success is True
    assert home.status == "HELD"

    # Reactivate
    react_res = await reactivate_home(home.id, ReactivateEntityRequest(reason="Investigation concluded"), super_admin=super_admin, db=mock_db)
    assert react_res.success is True
    assert home.status == "ACTIVE"

    # Archive
    arch_res = await archive_home(home.id, DeleteEntityRequest(reason="Workspace retired"), super_admin=super_admin, db=mock_db)
    assert arch_res.success is True
    assert home.status == "ARCHIVED"
    assert home.deleted_at is not None


@pytest.mark.asyncio
async def test_subscribers_listing_endpoint():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    sub = SubscriptionModel(
        id=uuid4(),
        home_id=uuid4(),
        status="ACTIVE",
        current_period_starts_at=datetime.now(timezone.utc),
        current_period_ends_at=datetime.now(timezone.utc) + timedelta(days=365),
        paid_member_seats=2,
        currency="USD"
    )

    mock_row = (sub, "Sunset Villa", sub.home_id, "vivek@zinfog.com", "Vivek", "Ozhzo Home Standard", "OZHZO_HOME", "TRIAL")

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[mock_row]))

    res = await list_subscribers(super_admin=super_admin, db=mock_db)
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].home_name == "Sunset Villa"
    assert res.data[0].user_email == "vivek@zinfog.com"
    assert res.data[0].coupon_code == "TRIAL"
    assert res.data[0].paid_seats == 2


@pytest.mark.asyncio
async def test_seed_demo_coupons():
    mock_db = AsyncMock()
    # First call returns None (not existing), so coupons get added
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    await seed_demo_coupons(mock_db)
    assert mock_db.add.call_count >= 2
    assert mock_db.commit.called
