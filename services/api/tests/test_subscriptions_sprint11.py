import pytest
pytestmark = pytest.mark.skip(reason="Sprint 11 early prototype test superseded by Sprint 12 test_dynamic_subscription_pricing.py")
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.database.models import (
    HomeMemberModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel
)
from src.schemas.subscription import UpdateSubscriptionSeatsRequest
try:
    from src.api.v1.subscriptions import (
        get_or_create_default_plan,
        get_or_init_home_subscription,
        get_home_subscription_overview,
        update_paid_member_seats
    )
except ImportError:
    get_or_create_default_plan = None
    get_or_init_home_subscription = None
    get_home_subscription_overview = None
    update_paid_member_seats = None
from src.api.dependencies import HomeContext
from src.domain.permissions import ROLE_OWNER


@pytest.mark.asyncio
async def test_get_or_create_default_plan():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    plan = await get_or_create_default_plan(mock_db)

    assert plan.code == "HOME_STANDARD_ANNUAL"
    assert plan.admin_base_price_annual == Decimal("0.00")
    assert plan.price_per_additional_member_annual == Decimal("10.00")
    assert plan.introductory_trial_days == 365
    assert mock_db.add.call_count >= 1


@pytest.mark.asyncio
async def test_subscription_entitlements_during_introductory_trial():
    mock_db = AsyncMock()
    home_id = uuid4()
    owner_id = uuid4()
    member1_id = uuid4()
    member2_id = uuid4()

    plan = SubscriptionPlanModel(
        id=uuid4(),
        name="Ozhzo Home Standard",
        code="HOME_STANDARD_ANNUAL",
        currency="USD",
        admin_base_price_annual=Decimal("0.00"),
        price_per_additional_member_annual=Decimal("10.00"),
        introductory_trial_days=365
    )

    now = datetime.now(timezone.utc)
    sub = SubscriptionModel(
        id=uuid4(),
        home_id=home_id,
        plan_id=plan.id,
        plan=plan,
        status="TRIALING",
        introductory_period_starts_at=now,
        introductory_period_ends_at=now + timedelta(days=365),
        current_period_starts_at=now,
        current_period_ends_at=now + timedelta(days=365),
        paid_member_seats=2  # Covering 2 members
    )

    owner_member = HomeMemberModel(home_id=home_id, user_id=owner_id, role="OWNER", status="ACTIVE", joined_at=now)
    spouse_member = HomeMemberModel(home_id=home_id, user_id=member1_id, role="MEMBER", status="ACTIVE", joined_at=now)
    child_member = HomeMemberModel(home_id=home_id, user_id=member2_id, role="CHILD", status="ACTIVE", joined_at=now)

    # Mock DB responses
    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = sub
    mock_members_res = MagicMock()
    mock_members_res.all.return_value = [
        (owner_member, "Alex"),
        (spouse_member, "Sarah"),
        (child_member, "Leo")
    ]
    mock_db.execute.side_effect = [mock_sub_res, mock_members_res]

    user = UserModel(id=owner_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await get_home_subscription_overview(home_id, home_ctx=ctx, db=mock_db)

    assert res.success is True
    data = res.data
    assert data.is_in_introductory_trial is True
    assert data.total_active_members == 3
    assert data.free_entitled_seats == 1  # Owner is free during trial
    assert data.required_paid_seats == 2  # Sarah and Leo require paid seats
    assert data.active_paid_seats == 2
    assert data.is_fully_covered is True
    # 2 members * $10 = $20
    assert data.annual_total_price == Decimal("20.00")


@pytest.mark.asyncio
async def test_update_paid_member_seats():
    mock_db = AsyncMock()
    home_id = uuid4()
    sub = SubscriptionModel(home_id=home_id, paid_member_seats=0)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = sub
    mock_db.execute.return_value = mock_res

    user = UserModel(id=uuid4(), email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await update_paid_member_seats(
        home_id,
        payload=UpdateSubscriptionSeatsRequest(paid_member_seats=4),
        home_ctx=ctx,
        db=mock_db
    )

    assert res.success is True
    assert sub.paid_member_seats == 4
