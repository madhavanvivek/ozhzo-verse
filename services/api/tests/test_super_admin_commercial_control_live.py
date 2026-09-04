import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from fastapi import HTTPException

from src.infrastructure.database.models import (
    UserModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    CouponModel,
    SubscriptionGrantModel,
    RegionConfigModel,
)
from src.api.v1.admin_subscriptions import (
    create_subscription_plan,
    update_subscription_plan,
    create_subscription_price,
    update_subscription_price,
)
from src.api.v1.admin_coupons import (
    create_coupon,
    update_coupon,
    create_direct_grant,
)
from src.api.v1.admin_regions import (
    create_region,
    update_region,
)
from src.api.v1.subscriptions import (
    validate_coupon_endpoint,
    ValidateCouponRequest,
)
from src.schemas.subscription import (
    CreateSubscriptionPlanRequest,
    UpdateSubscriptionPlanRequest,
    CreateSubscriptionPriceRequest,
    UpdateSubscriptionPriceRequest,
)
from src.schemas.coupon import (
    CreateCouponRequest,
    UpdateCouponRequest,
    CreateSubscriptionGrantRequest,
)
from src.schemas.admin_operational import (
    CreateRegionConfigRequest,
    UpdateRegionConfigRequest,
)


@pytest.mark.asyncio
async def test_super_admin_plan_crud_and_edit():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    plan_id = uuid4()
    existing_plan = SubscriptionPlanModel(
        id=plan_id,
        name="Home Standard OS",
        code="HOME_STANDARD",
        description="Household operating system",
        plan_type="HOME",
        status="ACTIVE",
        included_members=4,
        maximum_members=10,
        max_homes=5,
        additional_member_allowed=True,
        introductory_enabled=True,
        introductory_duration_days=365,
        introductory_price=Decimal("0.00"),
        created_at=datetime.now(timezone.utc),
    )

    mock_db.get.return_value = existing_plan

    # Super Admin edits the plan
    update_req = UpdateSubscriptionPlanRequest(
        name="Home Premium OS",
        description="Expanded household operating system",
        maximum_members=15,
        max_homes=8,
        introductory_duration_days=180,
    )

    res = await update_subscription_plan(plan_id=plan_id, payload=update_req, super_admin=super_admin, db=mock_db)

    assert res.success is True
    assert res.data.name == "Home Premium OS"
    assert existing_plan.name == "Home Premium OS"
    assert existing_plan.maximum_members == 15
    assert existing_plan.max_homes == 8


@pytest.mark.asyncio
async def test_super_admin_price_versioning():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    plan_id = uuid4()
    existing_plan = SubscriptionPlanModel(
        id=plan_id,
        name="Home Standard OS",
        code="HOME_STANDARD",
        status="ACTIVE",
    )
    mock_db.get.return_value = existing_plan

    # Version query returns existing version 1
    mock_db.execute.return_value = MagicMock(scalar=MagicMock(return_value=1))

    # Super Admin creates new price version (Price revision: 1799 -> 2499 INR)
    price_req = CreateSubscriptionPriceRequest(
        plan_id=plan_id,
        country="IN",
        region="South Asia",
        currency="INR",
        billing_period="ANNUAL",
        list_price=Decimal("2499.00"),
        additional_member_list_price=Decimal("599.00"),
        base_price=Decimal("2499.00"),
        additional_member_price=Decimal("599.00"),
        effective_from=datetime.now(timezone.utc),
    )

    res = await create_subscription_price(payload=price_req, super_admin=super_admin, db=mock_db)

    assert res.success is True
    assert res.data.version == 2
    assert res.data.list_price == Decimal("2499.00")
    assert res.data.country == "IN"
    assert res.data.currency == "INR"


@pytest.mark.asyncio
async def test_super_admin_coupon_lifecycle_and_customer_validation():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    customer = UserModel(id=uuid4(), email="customer@ozhzo.com", is_super_admin=False)
    mock_db = AsyncMock()

    coupon_id = uuid4()
    coupon = CouponModel(
        id=coupon_id,
        name="Launch Discount 50%",
        code="LAUNCH50",
        coupon_type="PERCENTAGE_DISCOUNT",
        discount_value=Decimal("50.00"),
        free_period_value=0,
        free_period_unit="MONTHS",
        eligibility_type="ANY_USER",
        status="ACTIVE",
        start_date=datetime.now(timezone.utc),
        redemptions_count=0,
        maximum_redemptions_per_user=1,
    )

    # 1. Customer validates coupon at 50%
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=coupon))
    val_res = await validate_coupon_endpoint(payload=ValidateCouponRequest(code="LAUNCH50"), current_user=customer, db=mock_db)
    assert val_res.success is True
    assert val_res.data["discount_value"] == 50.0

    # 2. Super Admin updates coupon discount to 60%
    mock_db.get.return_value = coupon
    edit_req = UpdateCouponRequest(
        discount_value=Decimal("60.00"),
        internal_reason="Increased promotional discount for festive season",
    )
    edit_res = await update_coupon(coupon_id=coupon_id, payload=edit_req, super_admin=super_admin, db=mock_db)
    assert edit_res.success is True
    assert coupon.discount_value == Decimal("60.00")

    # 3. Customer validates coupon again and receives updated 60% benefit
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=coupon))
    val_res_updated = await validate_coupon_endpoint(payload=ValidateCouponRequest(code="LAUNCH50"), current_user=customer, db=mock_db)
    assert val_res_updated.success is True
    assert val_res_updated.data["discount_value"] == 60.0

    # 4. Super Admin deactivates coupon
    deactivate_req = UpdateCouponRequest(status="INACTIVE", internal_reason="Campaign ended")
    await update_coupon(coupon_id=coupon_id, payload=deactivate_req, super_admin=super_admin, db=mock_db)
    assert coupon.status == "INACTIVE"

    # 5. Customer attempts to validate deactivated coupon -> receives 404
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        await validate_coupon_endpoint(payload=ValidateCouponRequest(code="LAUNCH50"), current_user=customer, db=mock_db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_super_admin_region_configuration_update():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    region = RegionConfigModel(
        id=uuid4(),
        country_code="IN",
        country_name="India",
        region="South Asia",
        currency="INR",
        default_plan_code="HOME_STANDARD",
        payment_gateway="RAZORPAY",
        tax_percentage=Decimal("18.00"),
        is_active=True,
        is_default=False,
        promotional_eligibility_enabled=True,
        metadata_json={},
    )

    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=region))

    # Super Admin updates tax % and gateway
    update_req = UpdateRegionConfigRequest(
        payment_gateway="STRIPE",
        tax_percentage=Decimal("12.00"),
    )

    res = await update_region(country_code="IN", payload=update_req, super_admin=super_admin, db=mock_db)

    assert res.success is True
    assert res.data.payment_gateway == "STRIPE"
    assert res.data.tax_percentage == Decimal("12.00")
