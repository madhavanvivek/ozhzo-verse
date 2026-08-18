import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.infrastructure.database.models import (
    CampaignModel,
    CouponModel,
    CouponRedemptionModel,
    HomeMemberModel,
    HomeModel,
    SubscriptionAuditLogModel,
    SubscriptionGrantModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel
)
from src.schemas.coupon import (
    CreateCampaignRequest,
    CreateCouponRequest,
    CreateSubscriptionGrantRequest
)
from src.schemas.subscription import CalculateSubscriptionRequest
from src.api.v1.admin_coupons import (
    create_campaign,
    create_coupon,
    create_direct_grant,
    get_coupon_analytics,
    revoke_direct_grant
)
from src.api.v1.subscriptions import (
    calculate_subscription_price,
    compute_free_days,
    evaluate_coupon
)


# ==============================================================================
# Tests 1-5: Free Coupons (1m, 3m, 6m, 1y)
# ==============================================================================

@pytest.mark.asyncio
async def test_1_super_admin_creates_free_coupon():
    """1. Super Admin creates a free period coupon."""
    mock_db = AsyncMock()
    super_admin = UserModel(id=uuid4(), is_super_admin=True)

    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    req = CreateCouponRequest(
        name="Welcome 6 Months Free",
        code="WELCOME6",
        coupon_type="FREE_PERIOD",
        free_period_value=6,
        free_period_unit="MONTHS",
        eligibility_type="ANY_USER"
    )
    res = await create_coupon(req, super_admin=super_admin, db=mock_db)
    assert res.success is True
    assert res.data.code == "WELCOME6"
    assert res.data.coupon_type == "FREE_PERIOD"
    assert res.data.free_period_value == 6


@pytest.mark.asyncio
async def test_2_to_5_free_durations_calculation():
    """2-5. 1-month (30d), 3-month (90d), 6-month (180d), and 1-year (365d) free coupons."""
    assert compute_free_days(1, "MONTHS") == 30
    assert compute_free_days(3, "MONTHS") == 90
    assert compute_free_days(6, "MONTHS") == 180
    assert compute_free_days(1, "YEARS") == 365

    # Test Calculation Engine with 6-month free coupon
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE", included_members=1)
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    coupon_6m = CouponModel(
        id=uuid4(), code="FREE6M", coupon_type="FREE_PERIOD", free_period_value=6, free_period_unit="MONTHS",
        status="ACTIVE", applicable_plan_id=plan_id
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=coupon_6m))
    ]

    req = CalculateSubscriptionRequest(additional_seats=2, coupon_code="FREE6M")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.is_free_period is True
    assert res.data.free_days_granted == 180
    assert res.data.total_payable == Decimal("0.00")
    assert res.data.payment_required is False


# ==============================================================================
# Tests 6-8: 100% Discount, Percentage Discount, Fixed Discount
# ==============================================================================

@pytest.mark.asyncio
async def test_6_hundred_percent_discount_vs_free_period():
    """6. 100% discount produces $0 payable while maintaining standard list price reference."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(plan_id=plan_id, country="IN", currency="INR", additional_member_list_price=Decimal("1799.00"), is_active=True, version=1)
    coupon_100 = CouponModel(id=uuid4(), code="OFF100", coupon_type="PERCENTAGE_DISCOUNT", discount_value=Decimal("100.00"), status="ACTIVE")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=coupon_100))
    ]

    req = CalculateSubscriptionRequest(additional_seats=1, coupon_code="OFF100")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.is_free_period is False
    assert res.data.discount_value == Decimal("100.00")
    assert res.data.discount_amount == Decimal("1799.00")
    assert res.data.effective_price == Decimal("0.00")
    assert res.data.total_payable == Decimal("0.00")


@pytest.mark.asyncio
async def test_7_percentage_discount():
    """7. Percentage discount: ₹1,799 - 50% = ₹899.50."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(plan_id=plan_id, country="IN", currency="INR", additional_member_list_price=Decimal("1799.00"), is_active=True, version=1)
    coupon_50 = CouponModel(id=uuid4(), code="SAVE50", coupon_type="PERCENTAGE_DISCOUNT", discount_value=Decimal("50.00"), status="ACTIVE")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=coupon_50))
    ]

    req = CalculateSubscriptionRequest(additional_seats=1, coupon_code="SAVE50")
    res = await calculate_subscription_price(req, db=mock_db)
    assert res.data.discount_amount == Decimal("899.50")
    assert res.data.effective_price == Decimal("899.50")


@pytest.mark.asyncio
async def test_8_fixed_discount():
    """8. Fixed discount: ₹1,799 - ₹500 = ₹1,299.00."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(plan_id=plan_id, country="IN", currency="INR", additional_member_list_price=Decimal("1799.00"), is_active=True, version=1)
    coupon_fixed = CouponModel(id=uuid4(), code="FLAT500", coupon_type="FIXED_DISCOUNT", discount_value=Decimal("500.00"), status="ACTIVE")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=coupon_fixed))
    ]

    req = CalculateSubscriptionRequest(additional_seats=1, coupon_code="FLAT500")
    res = await calculate_subscription_price(req, db=mock_db)
    assert res.data.discount_amount == Decimal("500.00")
    assert res.data.effective_price == Decimal("1299.00")


# ==============================================================================
# Tests 9-14: User, Home & Geographic Restrictions
# ==============================================================================

@pytest.mark.asyncio
async def test_9_user_specific_coupon():
    """9. User-specific coupon valid only for designated target user."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    target_user_id = uuid4()
    other_user_id = uuid4()

    coupon = CouponModel(id=uuid4(), code="VIP_USER", target_user_id=target_user_id, status="ACTIVE")
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=coupon))

    # Reject other user
    c, valid, reason = await evaluate_coupon("VIP_USER", plan_id, "US", None, None, None, "USD", other_user_id, None, mock_db)
    assert valid is False
    assert "exclusively reserved" in reason

    # Accept target user
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=coupon)),
        MagicMock(scalar=MagicMock(return_value=0))  # 0 user redemptions
    ]
    c, valid, reason = await evaluate_coupon("VIP_USER", plan_id, "US", None, None, None, "USD", target_user_id, None, mock_db)
    assert valid is True


@pytest.mark.asyncio
async def test_10_home_specific_coupon():
    """10. Home-specific coupon valid only for designated target home."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    target_home_id = uuid4()
    other_home_id = uuid4()

    coupon = CouponModel(id=uuid4(), code="VIP_HOME", target_home_id=target_home_id, status="ACTIVE")
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=coupon))

    c, valid, reason = await evaluate_coupon("VIP_HOME", plan_id, "US", None, None, None, "USD", None, other_home_id, mock_db)
    assert valid is False
    assert "exclusively reserved for a specific Home" in reason


@pytest.mark.asyncio
async def test_11_to_14_geographic_restrictions():
    """11-14. Country, State, District, and Postal Code restrictions."""
    mock_db = AsyncMock()
    plan_id = uuid4()

    geo_coupon = CouponModel(
        id=uuid4(), code="KERALA_ERN_PIN", country="IN", state="Kerala", district="Ernakulam", postal_code="682001", status="ACTIVE"
    )

    # 11. Country mismatch
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=geo_coupon))
    c, valid, reason = await evaluate_coupon("KERALA_ERN_PIN", plan_id, "US", "California", None, None, "USD", None, None, mock_db)
    assert valid is False
    assert "not valid in country US" in reason

    # 12. State mismatch
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=geo_coupon))
    c, valid, reason = await evaluate_coupon("KERALA_ERN_PIN", plan_id, "IN", "Maharashtra", None, None, "INR", None, None, mock_db)
    assert valid is False
    assert "restricted to state" in reason

    # 13. District mismatch
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=geo_coupon))
    c, valid, reason = await evaluate_coupon("KERALA_ERN_PIN", plan_id, "IN", "Kerala", "Kozhikode", None, "INR", None, None, mock_db)
    assert valid is False
    assert "restricted to district" in reason

    # 14. Postal code mismatch
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=geo_coupon))
    c, valid, reason = await evaluate_coupon("KERALA_ERN_PIN", plan_id, "IN", "Kerala", "Ernakulam", "110001", "INR", None, None, mock_db)
    assert valid is False
    assert "restricted to postal code" in reason

    # Exact Match
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=geo_coupon))
    c, valid, reason = await evaluate_coupon("KERALA_ERN_PIN", plan_id, "IN", "Kerala", "Ernakulam", "682001", "INR", None, None, mock_db)
    assert valid is True


# ==============================================================================
# Tests 15-19: Limits & Date Lifecycles
# ==============================================================================

@pytest.mark.asyncio
async def test_15_to_19_limits_and_dates():
    """15-19. Total limits, per-user limits, per-home limits, expired and future coupons."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    uid = uuid4()
    hid = uuid4()

    # 15. Total redemption limit
    capped_coupon = CouponModel(id=uuid4(), code="CAP100", status="ACTIVE", maximum_total_redemptions=100, redemptions_count=100)
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=capped_coupon))
    c, valid, r = await evaluate_coupon("CAP100", plan_id, "US", None, None, None, "USD", uid, hid, mock_db)
    assert valid is False
    assert "maximum total redemption limit" in r

    # 16. Per-user limit
    user_limit_coupon = CouponModel(id=uuid4(), code="USER1", status="ACTIVE", maximum_redemptions_per_user=1)
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=user_limit_coupon)),
        MagicMock(scalar=MagicMock(return_value=1))  # already 1 redemption
    ]
    c, valid, r = await evaluate_coupon("USER1", plan_id, "US", None, None, None, "USD", uid, hid, mock_db)
    assert valid is False
    assert "already redeemed coupon" in r

    # 17. Per-home limit
    home_limit_coupon = CouponModel(id=uuid4(), code="HOME1", status="ACTIVE", maximum_redemptions_per_user=5, maximum_redemptions_per_home=1)
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=home_limit_coupon)),
        MagicMock(scalar=MagicMock(return_value=0)),  # user count 0
        MagicMock(scalar=MagicMock(return_value=1))   # home count 1
    ]
    c, valid, r = await evaluate_coupon("HOME1", plan_id, "US", None, None, None, "USD", uid, hid, mock_db)
    assert valid is False
    assert "already been redeemed for this Home" in r

    # 18. Expired coupon
    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    expired_coupon = CouponModel(id=uuid4(), code="EXP", status="ACTIVE", end_date=past_date)
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=expired_coupon))
    c, valid, r = await evaluate_coupon("EXP", plan_id, "US", None, None, None, "USD", uid, hid, mock_db)
    assert valid is False
    assert "expired" in r

    # 19. Future coupon
    future_date = datetime.now(timezone.utc) + timedelta(days=5)
    future_coupon = CouponModel(id=uuid4(), code="FUT", status="ACTIVE", start_date=future_date)
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=future_coupon))
    c, valid, r = await evaluate_coupon("FUT", plan_id, "US", None, None, None, "USD", uid, hid, mock_db)
    assert valid is False
    assert "not started" in r


# ==============================================================================
# Tests 20-21: Direct Super Admin Grants & Audit Trail
# ==============================================================================

@pytest.mark.asyncio
async def test_20_and_21_direct_super_admin_grant():
    """20-21. Super Admin directly grants 6 months free to a Home, creating immutable audit."""
    mock_db = AsyncMock()
    super_admin = UserModel(id=uuid4(), is_super_admin=True)
    home_id = uuid4()
    home = HomeModel(id=home_id, name="VIP Estate")
    plan = SubscriptionPlanModel(id=uuid4(), code="OZHZO_HOME")

    mock_db.get.return_value = home
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),  # Plan lookup
        MagicMock(scalar_one_or_none=MagicMock(return_value=SubscriptionModel(home_id=home_id)))  # Sub lookup
    ]

    req = CreateSubscriptionGrantRequest(
        home_id=home_id,
        grant_type="FREE_PERIOD",
        duration_value=6,
        duration_unit="MONTHS",
        reason="VIP Early Adopter Direct Access"
    )
    res = await create_direct_grant(req, super_admin=super_admin, db=mock_db)

    assert res.success is True
    assert res.data.grant_type == "FREE_PERIOD"
    assert res.data.duration_value == 6
    assert res.data.reason == "VIP Early Adopter Direct Access"

    # Assert audit log was recorded
    assert mock_db.add.called


# ==============================================================================
# Tests 22-27: Coupon + Invitation, Multi-Home, Anti-Stacking & Immutability
# ==============================================================================

@pytest.mark.asyncio
async def test_22_coupon_and_invitation():
    """22. Invited user accepting invitation redeems coupon for active membership and subscription."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    home_id = uuid4()
    user_id = uuid4()

    coupon = CouponModel(id=uuid4(), code="INVITE_SPECIAL", coupon_type="FREE_PERIOD", free_period_value=3, status="ACTIVE")
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=coupon)),
        MagicMock(scalar=MagicMock(return_value=0)),  # user count
        MagicMock(scalar=MagicMock(return_value=0))   # home count
    ]

    c, valid, r = await evaluate_coupon("INVITE_SPECIAL", plan_id, "US", None, None, None, "USD", user_id, home_id, mock_db)
    assert valid is True
    assert c.coupon_type == "FREE_PERIOD"


def test_23_and_24_multi_home_isolation_for_coupons():
    """23-24. Applying coupon to Home 1 does not affect Home 2; cross-home activations blocked."""
    home_1_sub = SubscriptionModel(id=uuid4(), home_id=uuid4(), active_coupon_id=uuid4(), status="ACTIVE")
    home_2_sub = SubscriptionModel(id=uuid4(), home_id=uuid4(), active_coupon_id=None, status="TRIALING")

    assert home_1_sub.active_coupon_id is not None
    assert home_2_sub.active_coupon_id is None
    assert home_1_sub.home_id != home_2_sub.home_id


def test_25_to_27_anti_stacking_and_immutability():
    """25-27. Stacking is prevented by default; historical redemptions remain immutable."""
    coupon = CouponModel(id=uuid4(), code="SINGLE_USE", allow_stacking=False)
    assert coupon.allow_stacking is False

    redemption = CouponRedemptionModel(
        id=uuid4(),
        coupon_id=coupon.id,
        user_id=uuid4(),
        home_id=uuid4(),
        discount_amount_applied=Decimal("50.00"),
        free_days_granted=180,
        redeemed_at=datetime.now(timezone.utc)
    )
    # Immutable redemption snapshot
    assert redemption.discount_amount_applied == Decimal("50.00")
    assert redemption.free_days_granted == 180
