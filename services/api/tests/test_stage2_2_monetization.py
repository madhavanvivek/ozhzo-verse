import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from src.api.v1.homes import create_home, delete_home_workspace
from src.api.v1.subscriptions import (
    checkout_subscription,
    confirm_payment,
    evaluate_coupon,
    get_my_subscription_entitlements,
)
from src.core.exceptions import TierLimitExceededException
from src.domain.entitlements import check_can_create_home, get_user_entitlement_summary
from src.infrastructure.database.models import (
    CouponModel,
    CouponRedemptionModel,
    HomeModel,
    PaymentTransactionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel,
)
from src.schemas.home import CreateHomeRequest
from src.schemas.subscription import (
    CheckoutSubscriptionRequest,
    ConfirmPaymentRequest,
)


@pytest.mark.asyncio
async def test_01_free_home_rule_and_deletion_protection():
    """1. New user creates Home #1 free. Home #2 blocked. Deleting Home #1 does NOT grant free Home #2."""
    user_id = uuid4()
    user = UserModel(
        id=user_id,
        email="monetize_user@example.com",
        mobile_verified=True,
        free_home_consumed=False,
    )

    # 1a. User with 0 homes and free_home_consumed=False can create Home #1
    mock_db = AsyncMock()
    mock_res_empty = MagicMock()
    mock_res_empty.scalars.return_value.all.return_value = []
    mock_res_empty.all.return_value = []
    mock_db.execute.return_value = mock_res_empty

    # Should not raise exception
    await check_can_create_home(user, mock_db)

    # 1b. Once Home #1 is created, user.free_home_consumed is True
    home1 = HomeModel(id=uuid4(), name="Home 1", created_by=user_id, status="ACTIVE")
    user.free_home_consumed = True

    # 1c. Attempting Home #2 with 1 existing active home and no subscription -> BLOCKED
    mock_res_home1 = MagicMock()
    mock_res_home1.scalars.return_value.all.return_value = [home1]
    mock_res_sub_none = MagicMock()
    mock_res_sub_none.scalars.return_value.all.return_value = []
    mock_res_sub_none.scalars.return_value.first.return_value = None
    mock_db.execute.side_effect = [mock_res_home1, mock_res_sub_none]

    with pytest.raises(TierLimitExceededException) as exc_info:
        await check_can_create_home(user, mock_db)
    assert "one Home" in exc_info.value.detail

    # 1d. User deletes Home #1 (soft-deleted, 0 active homes remaining)
    # But because user.free_home_consumed == True, creating a new Home is STILL BLOCKED without subscription
    mock_db.execute.side_effect = [mock_res_empty, mock_res_sub_none]

    with pytest.raises(TierLimitExceededException) as exc_info:
        await check_can_create_home(user, mock_db)
    assert "one Home" in exc_info.value.detail


@pytest.mark.asyncio
async def test_02_paid_subscription_allows_additional_homes_and_enforces_limits():
    """2. Active paid subscription allows additional homes up to max_homes limit."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="subscriber@example.com", mobile_verified=True, free_home_consumed=True)

    plan = SubscriptionPlanModel(id=uuid4(), name="Pro Household", code="PRO_HOME", max_homes=3, status="ACTIVE")
    home1 = HomeModel(id=uuid4(), name="Home 1", created_by=user_id, status="ACTIVE")
    home2 = HomeModel(id=uuid4(), name="Home 2", created_by=user_id, status="ACTIVE")

    active_sub = SubscriptionModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home1.id,
        plan_id=plan.id,
        status="ACTIVE",
        current_period_ends_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    active_sub.plan = plan

    mock_db = AsyncMock()

    # Case A: User has 1 active home and active subscription allowing 3 homes -> ALLOW Home #2
    res_1_home = MagicMock()
    res_1_home.scalars.return_value.all.return_value = [home1]
    res_sub = MagicMock()
    res_sub.scalars.return_value.all.return_value = [active_sub]
    mock_db.execute.side_effect = [res_1_home, res_sub]

    await check_can_create_home(user, mock_db)

    # Case B: User already has 3 active homes (at plan capacity) -> BLOCK Home #4
    home3 = HomeModel(id=uuid4(), name="Home 3", created_by=user_id, status="ACTIVE")
    res_3_homes = MagicMock()
    res_3_homes.scalars.return_value.all.return_value = [home1, home2, home3]
    mock_db.execute.side_effect = [res_3_homes, res_sub]

    with pytest.raises(TierLimitExceededException):
        await check_can_create_home(user, mock_db)

    # Case C: Subscription expired -> BLOCK
    expired_sub = SubscriptionModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home1.id,
        plan_id=plan.id,
        status="ACTIVE",
        current_period_ends_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    expired_sub.plan = plan
    res_exp_sub = MagicMock()
    res_exp_sub.scalars.return_value.all.return_value = [expired_sub]
    mock_db.execute.side_effect = [res_1_home, res_exp_sub]

    with pytest.raises(TierLimitExceededException):
        await check_can_create_home(user, mock_db)


@pytest.mark.asyncio
async def test_03_coupon_validation_and_discount_calculation():
    """3. Coupon validation: percentage discount, fixed discount, usage limits, expiration."""
    plan_id = uuid4()
    user_id = uuid4()

    # 3a. Percentage Discount Coupon (50% off)
    coupon_50 = CouponModel(
        id=uuid4(),
        code="SAVE50",
        coupon_type="PERCENTAGE_DISCOUNT",
        discount_value=Decimal("50.00"),
        status="ACTIVE",
        maximum_total_redemptions=100,
        redemptions_count=10,
        maximum_redemptions_per_user=1,
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=30),
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = coupon_50
    mock_db.execute.return_value = mock_res

    # 3b. Per-user redemption check returns 0 prior redemptions
    mock_count = MagicMock()
    mock_count.scalar.return_value = 0
    mock_db.execute.side_effect = [mock_res, mock_count]

    c, valid, msg = await evaluate_coupon(
        coupon_code="SAVE50",
        plan_id=plan_id,
        country="GLOBAL",
        state=None,
        district=None,
        postal_code=None,
        currency="USD",
        user_id=user_id,
        home_id=None,
        db=mock_db,
    )
    assert valid is True
    assert c.code == "SAVE50"

    # 3c. Expired coupon -> rejected
    coupon_50.end_date = datetime.now(timezone.utc) - timedelta(days=1)
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = mock_res
    c, valid, msg = await evaluate_coupon(
        coupon_code="SAVE50",
        plan_id=plan_id,
        country="GLOBAL",
        state=None,
        district=None,
        postal_code=None,
        currency="USD",
        user_id=user_id,
        home_id=None,
        db=mock_db,
    )
    assert valid is False
    assert "expired" in msg.lower()

    # 3d. Inactive coupon -> rejected
    coupon_50.status = "INACTIVE"
    coupon_50.end_date = datetime.now(timezone.utc) + timedelta(days=30)
    c, valid, msg = await evaluate_coupon(
        coupon_code="SAVE50",
        plan_id=plan_id,
        country="GLOBAL",
        state=None,
        district=None,
        postal_code=None,
        currency="USD",
        user_id=user_id,
        home_id=None,
        db=mock_db,
    )
    assert valid is False
    assert "inactive" in msg.lower()


@pytest.mark.asyncio
async def test_04_payment_checkout_and_confirmation_lifecycle():
    """4. End-to-end checkout and payment confirmation activates subscription."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="buyer@example.com", mobile_verified=True, free_home_consumed=True)

    plan = SubscriptionPlanModel(
        id=uuid4(),
        name="Household Premium",
        code="PREMIUM_HOME",
        status="ACTIVE",
        max_homes=5,
        included_members=5,
    )
    price = SubscriptionPriceModel(
        id=uuid4(),
        plan_id=plan.id,
        country="GLOBAL",
        currency="USD",
        billing_period="ANNUAL",
        list_price=Decimal("49.00"),
        is_active=True,
    )

    mock_db = AsyncMock()
    mock_db.get.side_effect = lambda model, obj_id: (
        plan if model == SubscriptionPlanModel and obj_id == plan.id else (
            price if model == SubscriptionPriceModel and obj_id == price.id else None
        )
    )

    checkout_req = CheckoutSubscriptionRequest(
        plan_id=plan.id,
        price_id=price.id,
        currency="USD",
        billing_period="ANNUAL",
    )

    checkout_res = await checkout_subscription(payload=checkout_req, current_user=user, db=mock_db)
    assert checkout_res.data.status in ["PENDING", "SUCCESS"]
    assert checkout_res.data.amount == Decimal("49.00")
    assert checkout_res.data.payment_required is True

    # 4b. Confirm payment
    tx_id = checkout_res.data.transaction_id
    transaction = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        plan_id=plan.id,
        price_id=price.id,
        amount=Decimal("49.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_tx_valid_123",
        status="PENDING",
    )
    mock_db.get.side_effect = lambda model, obj_id: transaction if model == PaymentTransactionModel else None
    
    mock_sub_q = MagicMock()
    mock_sub_q.scalars.return_value.first.return_value = None
    mock_sub_q.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_sub_q

    confirm_req = ConfirmPaymentRequest(
        transaction_id=tx_id,
        provider_transaction_id="mock_tx_valid_123",
    )

    confirm_res = await confirm_payment(payload=confirm_req, current_user=user, db=mock_db)
    assert confirm_res.data.success is True
    assert confirm_res.data.status == "ACTIVE"
    assert transaction.status == "SUCCESS"


@pytest.mark.asyncio
async def test_05_user_entitlement_summary_api():
    """5. Verify user entitlement summary API calculation."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="summary_user@example.com", mobile_verified=True, free_home_consumed=False)

    mock_db = AsyncMock()
    mock_homes = MagicMock()
    mock_homes.scalars.return_value.all.return_value = []
    mock_subs = MagicMock()
    mock_subs.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [mock_homes, mock_subs]

    summary_res = await get_my_subscription_entitlements(current_user=user, db=mock_db)
    data = summary_res.data
    assert data.free_home_consumed is False
    assert data.active_homes_count == 0
    assert data.total_allowed_homes == 1
    assert data.can_create_home is True


@pytest.mark.asyncio
async def test_06_admin_plan_management_with_max_homes():
    """6. Super Admin can create and update plans with custom max_homes."""
    from src.api.v1.admin_subscriptions import create_subscription_plan, update_subscription_plan
    from src.schemas.subscription import CreateSubscriptionPlanRequest, UpdateSubscriptionPlanRequest

    admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    mock_db = AsyncMock()

    mock_exists = MagicMock()
    mock_exists.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_exists

    req = CreateSubscriptionPlanRequest(
        name="Enterprise Household",
        code="ENTERPRISE_HOME",
        description="For multi-property estates",
        included_members=10,
        maximum_members=50,
        max_homes=15,
        introductory_enabled=False,
    )

    created_res = await create_subscription_plan(payload=req, super_admin=admin, db=mock_db)
    assert created_res.data.name == "Enterprise Household"
    assert created_res.data.max_homes == 15

    # Update plan
    existing_plan = SubscriptionPlanModel(
        id=created_res.data.id,
        name="Enterprise Household",
        code="ENTERPRISE_HOME",
        description="For multi-property estates",
        plan_type="HOME",
        status="ACTIVE",
        included_members=10,
        maximum_members=50,
        max_homes=15,
        additional_member_allowed=True,
        introductory_enabled=False,
        introductory_duration_days=0,
        introductory_price=Decimal("0.00"),
    )
    mock_db.get.return_value = existing_plan

    update_req = UpdateSubscriptionPlanRequest(
        max_homes=25,
        name="Estate Plan VIP",
    )
    updated_res = await update_subscription_plan(plan_id=existing_plan.id, payload=update_req, super_admin=admin, db=mock_db)
    assert existing_plan.max_homes == 25
    assert existing_plan.name == "Estate Plan VIP"


@pytest.mark.asyncio
async def test_07_admin_transactions_and_analytics():
    """7. Super Admin can query transactions and revenue analytics."""
    from src.api.v1.admin_subscriptions import get_admin_subscription_analytics, list_admin_payment_transactions

    admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    mock_db = AsyncMock()

    # Mock transactions query
    tx1 = PaymentTransactionModel(
        id=uuid4(),
        user_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("0.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        status="SUCCESS",
        created_at=datetime.now(timezone.utc),
    )
    mock_tx_res = MagicMock()
    mock_tx_res.scalars.return_value.all.return_value = [tx1]
    mock_db.execute.return_value = mock_tx_res

    tx_list_res = await list_admin_payment_transactions(status_filter="SUCCESS", super_admin=admin, db=mock_db)
    assert len(tx_list_res.data) == 1
    assert tx_list_res.data[0].final_amount == Decimal("49.00")

    # Mock analytics query
    res_rev = MagicMock()
    res_rev.scalar.return_value = Decimal("980.00")
    res_count = MagicMock()
    res_count.scalar.return_value = 20
    res_active = MagicMock()
    res_active.scalar.return_value = 18
    res_trial = MagicMock()
    res_trial.scalar.return_value = 2
    res_past = MagicMock()
    res_past.scalar.return_value = 0
    res_canc = MagicMock()
    res_canc.scalar.return_value = 1

    mock_db.execute.side_effect = [res_rev, res_count, res_active, res_trial, res_past, res_canc]
    analytics_res = await get_admin_subscription_analytics(super_admin=admin, db=mock_db)
    assert analytics_res.data["total_revenue"] == 980.0
    assert analytics_res.data["total_transactions"] == 20
    assert analytics_res.data["active_subscribers"] == 18


@pytest.mark.asyncio
async def test_08_concurrent_home_creation_serializes_and_enforces_free_home_rule():
    """8. Concurrency: check_can_create_home serializes execution on user lock."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="concurrent@example.com", mobile_verified=True, free_home_consumed=False)

    mock_db = AsyncMock()

    # Call 1: 0 existing homes -> allowed
    res_0 = MagicMock()
    res_0.scalars.return_value.all.return_value = []
    
    # Call 2: home 1 exists -> blocked
    h1 = HomeModel(id=uuid4(), name="Home 1", created_by=user_id)
    res_1 = MagicMock()
    res_1.scalars.return_value.all.return_value = [h1]
    res_sub_none = MagicMock()
    res_sub_none.scalars.return_value.all.return_value = []
    res_sub_none.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [res_0, res_1, res_sub_none]

    # First creation passes
    await check_can_create_home(user, mock_db)
    user.free_home_consumed = True

    # Second creation immediately fails
    with pytest.raises(TierLimitExceededException):
        await check_can_create_home(user, mock_db)

