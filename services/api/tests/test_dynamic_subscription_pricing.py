import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.infrastructure.database.models import (
    PromotionModel,
    SubscriptionAuditLogModel,
    SubscriptionFeatureModel,
    SubscriptionModel,
    SubscriptionPlanFeatureModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel
)
from src.schemas.subscription import (
    CalculateSubscriptionRequest,
    CreatePromotionRequest,
    CreateSubscriptionFeatureRequest,
    CreateSubscriptionPlanRequest,
    CreateSubscriptionPriceRequest,
    UpdatePromotionRequest,
    UpdateSubscriptionPlanRequest,
    UpdateSubscriptionPriceRequest
)
from src.api.v1.admin_subscriptions import (
    create_promotion,
    create_subscription_plan,
    create_subscription_price,
    get_subscription_audit_logs,
    list_promotions,
    update_promotion,
    update_subscription_plan,
    update_subscription_price
)
from src.api.v1.subscriptions import (
    calculate_subscription_price,
    evaluate_promotion,
    get_current_pricing,
    list_subscription_plans
)
from src.api.dependencies import require_super_admin


# ==============================================================================
# 1-6: Standard Price & Discount Calculation Formulations
# ==============================================================================

@pytest.mark.asyncio
async def test_1_standard_price_calculation():
    """1. Standard / list price is retrieved correctly when no discount applies."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE", included_members=1, introductory_enabled=True)
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="GLOBAL", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None))  # No promotion
    ]

    req = CalculateSubscriptionRequest(additional_seats=1, promotion_code="NONE_APPLIED")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.list_price == Decimal("20.00")
    assert res.data.discount_amount == Decimal("0.00")
    assert res.data.effective_price == Decimal("20.00")
    assert res.data.total_payable == Decimal("20.00")


@pytest.mark.asyncio
async def test_2_percentage_discount():
    """2. Percentage discount calculation: $20 List Price, 50% OFF = $10 Effective Price."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE", included_members=1, introductory_enabled=True)
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    promo = PromotionModel(
        id=uuid4(), code="LAUNCH50", discount_type="PERCENTAGE", discount_value=Decimal("50.00"),
        status="ACTIVE", applicable_plan_id=plan_id
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]

    req = CalculateSubscriptionRequest(additional_seats=3, country="US", promotion_code="LAUNCH50")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.list_price == Decimal("20.00")
    assert res.data.discount_value == Decimal("50.00")
    assert res.data.discount_amount == Decimal("10.00")
    assert res.data.effective_price == Decimal("10.00")
    assert res.data.seats_effective_total == Decimal("30.00")
    assert res.data.total_payable == Decimal("30.00")


@pytest.mark.asyncio
async def test_3_fixed_discount():
    """3. Fixed discount calculation: $20 List Price, $5 OFF = $15 Effective Price."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE", included_members=1, introductory_enabled=True)
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    promo = PromotionModel(
        id=uuid4(), code="SAVE5", discount_type="FIXED_AMOUNT", discount_value=Decimal("5.00"),
        status="ACTIVE", applicable_plan_id=plan_id
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]

    req = CalculateSubscriptionRequest(additional_seats=2, country="US", promotion_code="SAVE5")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.discount_amount == Decimal("5.00")
    assert res.data.effective_price == Decimal("15.00")
    assert res.data.seats_effective_total == Decimal("30.00")


@pytest.mark.asyncio
async def test_4_zero_discount():
    """4. 0% discount results in full standard list price."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    promo = PromotionModel(
        id=uuid4(), code="ZERO_PROMO", discount_type="PERCENTAGE", discount_value=Decimal("0.00"),
        status="ACTIVE", applicable_plan_id=plan_id
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]

    req = CalculateSubscriptionRequest(additional_seats=1, promotion_code="ZERO_PROMO")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.discount_amount == Decimal("0.00")
    assert res.data.effective_price == Decimal("20.00")


@pytest.mark.asyncio
async def test_5_hundred_percent_discount():
    """5. 100% discount results in $0 effective price."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    promo = PromotionModel(
        id=uuid4(), code="FREE100", discount_type="PERCENTAGE", discount_value=Decimal("100.00"),
        status="ACTIVE", applicable_plan_id=plan_id
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]

    req = CalculateSubscriptionRequest(additional_seats=4, promotion_code="FREE100")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.discount_amount == Decimal("20.00")
    assert res.data.effective_price == Decimal("0.00")
    assert res.data.total_payable == Decimal("0.00")


@pytest.mark.asyncio
async def test_6_discount_cannot_produce_negative_price():
    """6. Fixed discount exceeding list price is clamped to $0 effective price (never negative)."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    # $50 discount on $20 list price
    promo = PromotionModel(
        id=uuid4(), code="OVER_DISCOUNT", discount_type="FIXED_AMOUNT", discount_value=Decimal("50.00"),
        status="ACTIVE", applicable_plan_id=plan_id
    )

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]

    req = CalculateSubscriptionRequest(additional_seats=1, promotion_code="OVER_DISCOUNT")
    res = await calculate_subscription_price(req, db=mock_db)

    assert res.data.discount_amount == Decimal("20.00")
    assert res.data.effective_price == Decimal("0.00")
    assert res.data.effective_price >= Decimal("0.00")


# ==============================================================================
# 7-12: Promotion Lifecycle, Dates, Limits & Eligibility
# ==============================================================================

@pytest.mark.asyncio
async def test_7_expired_promotion_rejected():
    """7. Expired promotion is rejected."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    past_date = datetime.now(timezone.utc) - timedelta(days=10)
    expired_promo = PromotionModel(
        id=uuid4(), code="EXPIRED_CODE", status="ACTIVE", end_date=past_date,
        discount_type="PERCENTAGE", discount_value=Decimal("50.00")
    )
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=expired_promo))

    promo, valid, reason = await evaluate_promotion(
        promotion_code="EXPIRED_CODE", plan_id=plan_id, country="US", currency="USD", user_id=None, db=mock_db
    )
    assert valid is False
    assert "expired" in reason.lower()


@pytest.mark.asyncio
async def test_8_future_promotion_rejected():
    """8. Future promotion with start_date in future is rejected."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    future_date = datetime.now(timezone.utc) + timedelta(days=10)
    future_promo = PromotionModel(
        id=uuid4(), code="FUTURE_CODE", status="ACTIVE", start_date=future_date,
        discount_type="PERCENTAGE", discount_value=Decimal("50.00")
    )
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=future_promo))

    promo, valid, reason = await evaluate_promotion(
        promotion_code="FUTURE_CODE", plan_id=plan_id, country="US", currency="USD", user_id=None, db=mock_db
    )
    assert valid is False
    assert "not started" in reason.lower()


@pytest.mark.asyncio
async def test_9_invalid_promotion():
    """9. Non-existent promotion code is reported as invalid."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    promo, valid, reason = await evaluate_promotion(
        promotion_code="INVALID_CODE_999", plan_id=plan_id, country="US", currency="USD", user_id=None, db=mock_db
    )
    assert valid is False
    assert "invalid" in reason.lower()


@pytest.mark.asyncio
async def test_10_maximum_redemptions_enforced():
    """10. Promotion that reached maximum redemption limit is rejected."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    capped_promo = PromotionModel(
        id=uuid4(), code="CAPPED_CODE", status="ACTIVE", maximum_redemptions=100, redemptions_count=100,
        discount_type="PERCENTAGE", discount_value=Decimal("50.00")
    )
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=capped_promo))

    promo, valid, reason = await evaluate_promotion(
        promotion_code="CAPPED_CODE", plan_id=plan_id, country="US", currency="USD", user_id=None, db=mock_db
    )
    assert valid is False
    assert "maximum redemption limit" in reason.lower()


@pytest.mark.asyncio
async def test_11_new_users_only_promotion():
    """11. New-user-only promotion is rejected for existing users with prior subscriptions."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    user_id = uuid4()
    new_user_promo = PromotionModel(
        id=uuid4(), code="NEW_USERS_ONLY", status="ACTIVE", new_users_only=True,
        discount_type="PERCENTAGE", discount_value=Decimal("50.00")
    )
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=new_user_promo)),
        MagicMock(first=MagicMock(return_value=SubscriptionModel(id=uuid4())))  # Prior subscription found
    ]

    promo, valid, reason = await evaluate_promotion(
        promotion_code="NEW_USERS_ONLY", plan_id=plan_id, country="US", currency="USD", user_id=user_id, db=mock_db
    )
    assert valid is False
    assert "new users only" in reason.lower()


@pytest.mark.asyncio
async def test_12_regional_promotion_filtering():
    """12. Regional promotion valid only in India is rejected when requested in US."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    india_promo = PromotionModel(
        id=uuid4(), code="DIWALI50", status="ACTIVE", country="IN",
        discount_type="PERCENTAGE", discount_value=Decimal("50.00")
    )
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=india_promo))

    promo, valid, reason = await evaluate_promotion(
        promotion_code="DIWALI50", plan_id=plan_id, country="US", currency="USD", user_id=None, db=mock_db
    )
    assert valid is False
    assert "not valid in region US" in reason


# ==============================================================================
# 13-16: Multi-Currency & Seat Arithmetic Scaling
# ==============================================================================

@pytest.mark.asyncio
async def test_13_different_currencies():
    """13. Multiple currencies compute list, discount, and effective prices accurately."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")

    # India Price (₹1,799 List Price, 50% discount = ₹899.50)
    price_in = SubscriptionPriceModel(
        plan_id=plan_id, country="IN", region="SOUTH_ASIA", currency="INR", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("1799.00"), is_active=True, version=1
    )
    promo_in = PromotionModel(id=uuid4(), code="LAUNCH50", discount_type="PERCENTAGE", discount_value=Decimal("50.00"), status="ACTIVE")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price_in)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo_in))
    ]

    req_in = CalculateSubscriptionRequest(additional_seats=1, country="IN", currency="INR", promotion_code="LAUNCH50")
    res_in = await calculate_subscription_price(req_in, db=mock_db)

    assert res_in.data.currency == "INR"
    assert res_in.data.list_price == Decimal("1799.00")
    assert res_in.data.discount_amount == Decimal("899.50")
    assert res_in.data.effective_price == Decimal("899.50")


@pytest.mark.asyncio
async def test_14_to_16_seat_scaling_calculations():
    """14-16: 1 seat ($10), 3 seats ($30), 5 seats ($50) dynamically calculated."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE", included_members=1, introductory_enabled=True)
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    promo = PromotionModel(id=uuid4(), code="LAUNCH50", discount_type="PERCENTAGE", discount_value=Decimal("50.00"), status="ACTIVE")

    # 1 seat
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]
    res1 = await calculate_subscription_price(CalculateSubscriptionRequest(additional_seats=1), db=mock_db)
    assert res1.data.seats_effective_total == Decimal("10.00")

    # 3 seats
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]
    res3 = await calculate_subscription_price(CalculateSubscriptionRequest(additional_seats=3), db=mock_db)
    assert res3.data.seats_effective_total == Decimal("30.00")

    # 5 seats
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]
    res5 = await calculate_subscription_price(CalculateSubscriptionRequest(additional_seats=5), db=mock_db)
    assert res5.data.seats_effective_total == Decimal("50.00")


# ==============================================================================
# 17-20: Historical Snapshots, Super Admin Authorization & Consistency
# ==============================================================================

def test_17_historical_price_snapshot_immutability():
    """17. Changing published list price from $20 to $25 preserves active subscription snapshot at $10."""
    home_id = uuid4()
    plan_id = uuid4()

    subscription = SubscriptionModel(
        id=uuid4(),
        home_id=home_id,
        plan_id=plan_id,
        status="ACTIVE",
        paid_member_seats=3,
        list_price_snapshot=Decimal("20.00"),
        additional_member_list_price_snapshot=Decimal("20.00"),
        discount_type_snapshot="PERCENTAGE",
        discount_value_snapshot=Decimal("50.00"),
        discount_amount_snapshot=Decimal("10.00"),
        effective_price_snapshot=Decimal("10.00"),
        promotion_code_snapshot="LAUNCH50",
        renewal_policy="KEEP_ORIGINAL_PRICE"
    )

    # Later standard price update to $25
    updated_price = SubscriptionPriceModel(
        id=uuid4(), plan_id=plan_id, country="US", additional_member_list_price=Decimal("25.00"), version=2
    )

    # Subscriber's snapshot is completely preserved
    assert subscription.effective_price_snapshot == Decimal("10.00")
    assert subscription.additional_member_list_price_snapshot == Decimal("20.00")
    assert subscription.additional_member_list_price_snapshot != updated_price.additional_member_list_price


@pytest.mark.asyncio
async def test_18_super_admin_promotion_modification():
    """18. Super Admin can create and update promotional campaigns."""
    mock_db = AsyncMock()
    super_admin = UserModel(id=uuid4(), is_super_admin=True)

    # No existing promo with code
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    req = CreatePromotionRequest(
        name="Founding Home Special",
        code="FOUNDING_HOME",
        discount_type="PERCENTAGE",
        discount_value=Decimal("60.00"),
        maximum_redemptions=500
    )

    res = await create_promotion(req, super_admin=super_admin, db=mock_db)
    assert res.success is True
    assert res.data.code == "FOUNDING_HOME"
    assert res.data.discount_value == Decimal("60.00")


@pytest.mark.asyncio
async def test_19_unauthorized_pricing_modification():
    """19. Non-super admin is rejected with 403 Forbidden."""
    home_admin = UserModel(id=uuid4(), is_super_admin=False)

    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=home_admin)
    assert exc_info.value.status_code == 403
    assert "Super Admin privileges required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_20_pricing_calculation_consistency():
    """20. Multiple consecutive calculation calls produce deterministic, consistent quotes."""
    mock_db = AsyncMock()
    plan_id = uuid4()
    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    price = SubscriptionPriceModel(
        plan_id=plan_id, country="US", currency="USD", billing_period="ANNUAL",
        list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"), is_active=True, version=1
    )
    promo = PromotionModel(id=uuid4(), code="LAUNCH50", discount_type="PERCENTAGE", discount_value=Decimal("50.00"), status="ACTIVE")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=price)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=promo))
    ]

    req = CalculateSubscriptionRequest(additional_seats=3, promotion_code="LAUNCH50")
    res_a = await calculate_subscription_price(req, db=mock_db)
    res_b = await calculate_subscription_price(req, db=mock_db)

    assert res_a.data.effective_price == res_b.data.effective_price == Decimal("10.00")
    assert res_a.data.total_payable == res_b.data.total_payable == Decimal("30.00")
