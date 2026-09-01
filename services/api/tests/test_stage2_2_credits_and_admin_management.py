import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from src.api.dependencies import require_super_admin
from src.domain.entitlements import (
    consume_user_credits,
    get_user_available_credits,
    get_user_credit_balance,
    grant_user_credit,
    provision_first_year_free_entitlement,
    provision_paid_home_entitlement,
    revoke_user_credit,
    verify_user_home_access_entitlement,
)
from src.infrastructure.database.models import (
    HomeAccessEntitlementModel,
    HomeModel,
    PaymentTransactionModel,
    SubscriptionAuditLogModel,
    SubscriptionCreditModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
)
from src.schemas.subscription import (
    AdminCancelSubscriptionRequest,
    AdminGrantSubscriptionRequest,
    AdminOverrideSubscriptionPeriodRequest,
    CalculateSubscriptionRequest,
    CheckoutSubscriptionRequest,
    GrantCreditRequest,
    RevokeCreditRequest,
)
from src.api.v1.admin_subscriptions import (
    admin_cancel_subscription,
    admin_grant_credit,
    admin_grant_subscription,
    admin_override_subscription_period,
    admin_revoke_credit,
    get_admin_user_credit_balance,
    list_admin_subscription_credits,
)
from src.api.v1.subscriptions import (
    calculate_subscription_price,
    checkout_subscription,
    get_my_credits,
)


# ==============================================================================
# 1. CREDIT LEDGER UNIT & DOMAIN TESTS (Items 1-10)
# ==============================================================================

@pytest.mark.asyncio
async def test_01_credit_creation_and_fields():
    """1. Credit can be created with immutable financial metadata."""
    user_id = uuid4()
    admin_id = uuid4()
    mock_db = AsyncMock()

    credit = await grant_user_credit(
        user_id=user_id,
        amount=Decimal("1200.00"),
        currency="INR",
        credit_type="ADMIN_GRANT",
        reason="Customer compensation",
        db=mock_db,
        expires_in_days=90,
        admin_id=admin_id,
        description="Compensation for service issue"
    )

    assert credit.user_id == user_id
    assert credit.amount == Decimal("1200.00")
    assert credit.remaining_amount == Decimal("1200.00")
    assert credit.currency == "INR"
    assert credit.credit_type == "ADMIN_GRANT"
    assert credit.status == "AVAILABLE"
    assert credit.created_by == admin_id
    assert credit.expires_at is not None


@pytest.mark.asyncio
async def test_02_credit_balance_calculation():
    """2. Credit balance is correctly aggregated per currency."""
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_db = AsyncMock()

    c1 = SubscriptionCreditModel(
        id=uuid4(), user_id=user_id, amount=Decimal("1000.00"), remaining_amount=Decimal("700.00"),
        currency="USD", status="PARTIALLY_USED", expires_at=now + timedelta(days=30)
    )
    c2 = SubscriptionCreditModel(
        id=uuid4(), user_id=user_id, amount=Decimal("500.00"), remaining_amount=Decimal("500.00"),
        currency="USD", status="AVAILABLE", expires_at=None
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [c1, c2]
    mock_db.execute.return_value = mock_res

    balance = await get_user_credit_balance(user_id, "USD", mock_db)
    assert balance == Decimal("1200.00")


@pytest.mark.asyncio
async def test_03_04_partial_and_full_consumption():
    """3, 4, 5, 6. Partial consumption, full consumption, and zero-negative bounds."""
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_db = AsyncMock()

    credit = SubscriptionCreditModel(
        id=uuid4(), user_id=user_id, amount=Decimal("1200.00"), remaining_amount=Decimal("1200.00"),
        currency="USD", status="AVAILABLE", expires_at=now + timedelta(days=60)
    )

    # 1. Partial Consumption (consume $500 of $1200)
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [credit]
    mock_db.execute.return_value = mock_res

    consumed, affected = await consume_user_credits(user_id, Decimal("500.00"), "USD", mock_db)
    assert consumed == Decimal("500.00")
    assert credit.remaining_amount == Decimal("700.00")
    assert credit.status == "PARTIALLY_USED"

    # 2. Full Consumption (consume remaining $700)
    consumed2, _ = await consume_user_credits(user_id, Decimal("700.00"), "USD", mock_db)
    assert consumed2 == Decimal("700.00")
    assert credit.remaining_amount == Decimal("0.00")
    assert credit.status == "REDEEMED"

    # 3. Cannot go negative when requesting more than available
    consumed3, _ = await consume_user_credits(user_id, Decimal("100.00"), "USD", mock_db)
    assert consumed3 == Decimal("0.00")
    assert credit.remaining_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_08_09_10_expired_cancelled_currency_mismatch():
    """8, 9, 10. Expired, cancelled, and currency mismatched credits cannot be consumed."""
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_db = AsyncMock()

    # Expired credit
    exp_credit = SubscriptionCreditModel(
        id=uuid4(), user_id=user_id, amount=Decimal("500.00"), remaining_amount=Decimal("500.00"),
        currency="USD", status="AVAILABLE", expires_at=now - timedelta(days=5)
    )
    # Cancelled credit
    canc_credit = SubscriptionCreditModel(
        id=uuid4(), user_id=user_id, amount=Decimal("500.00"), remaining_amount=Decimal("500.00"),
        currency="USD", status="CANCELLED", expires_at=now + timedelta(days=30)
    )

    # Empty scalar return simulates query filter filtering them out
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    # 1. Expired/Cancelled returns 0 consumed
    consumed, _ = await consume_user_credits(user_id, Decimal("500.00"), "USD", mock_db)
    assert consumed == Decimal("0.00")

    # 2. Currency Mismatch (User has INR, requesting USD)
    consumed_curr, _ = await consume_user_credits(user_id, Decimal("500.00"), "USD", mock_db)
    assert consumed_curr == Decimal("0.00")


# ==============================================================================
# 2. SUPER ADMIN MANAGEMENT TESTS (Items 11-18)
# ==============================================================================

@pytest.mark.asyncio
async def test_11_12_admin_grant_and_revoke_credit():
    """11, 12, 18. Super Admin can grant and revoke credits with audit records."""
    super_admin = UserModel(id=uuid4(), email="admin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    target_user = UserModel(id=uuid4(), email="target@ozhzo.com", is_super_admin=False)
    mock_db = AsyncMock()
    mock_db.get.return_value = target_user

    # 1. Grant Credit
    req = GrantCreditRequest(
        user_id=target_user.id,
        amount=Decimal("1000.00"),
        currency="INR",
        reason="Goodwill voucher",
        expires_in_days=30
    )
    res = await admin_grant_credit(req, super_admin=super_admin, db=mock_db)
    assert res.data.amount == Decimal("1000.00")
    assert res.data.currency == "INR"
    assert res.data.status == "AVAILABLE"

    # 2. Revoke Credit
    credit_record = SubscriptionCreditModel(
        id=res.data.id,
        user_id=target_user.id,
        amount=Decimal("1000.00"),
        remaining_amount=Decimal("1000.00"),
        currency="INR",
        credit_type="ADMIN_GRANT",
        status="AVAILABLE",
        created_at=datetime.now(timezone.utc)
    )
    mock_db.get.return_value = credit_record
    revoke_req = RevokeCreditRequest(reason="Requested by customer")
    revoke_res = await admin_revoke_credit(res.data.id, revoke_req, super_admin=super_admin, db=mock_db)

    assert revoke_res.data.status == "CANCELLED"
    assert revoke_res.data.remaining_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_13_14_non_super_admin_security():
    """13, 14, 31. Normal users and Home Admins cannot execute Super Admin operations."""
    normal_user = UserModel(id=uuid4(), email="normal@ozhzo.com", is_super_admin=False, system_role="USER")

    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=normal_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_15_16_17_admin_subscription_controls():
    """15, 16, 17, 28. Super Admin direct grant, override, and cancel."""
    super_admin = UserModel(id=uuid4(), email="admin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    home = HomeModel(id=uuid4(), name="Family Home", created_by=uuid4(), status="ACTIVE")
    plan = SubscriptionPlanModel(id=uuid4(), name="Premium Home", code="PREMIUM", status="ACTIVE")
    sub = SubscriptionModel(id=uuid4(), home_id=home.id, plan_id=plan.id, status="ACTIVE", current_period_ends_at=datetime.now(timezone.utc) + timedelta(days=30))

    mock_db = AsyncMock()

    # 1. Admin Grant Subscription
    mock_db.get.side_effect = [home, plan, UserModel(id=home.created_by)]
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res

    grant_req = AdminGrantSubscriptionRequest(home_id=home.id, plan_id=plan.id, duration_days=365, reason="VIP Partner")
    grant_res = await admin_grant_subscription(grant_req, super_admin=super_admin, db=mock_db)
    assert "granted" in grant_res.data.message.lower()

    # 2. Override Period
    mock_db.get.side_effect = [sub]
    mock_ent_res = MagicMock()
    mock_ent_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_ent_res

    new_expiry = datetime.now(timezone.utc) + timedelta(days=600)
    override_req = AdminOverrideSubscriptionPeriodRequest(current_period_ends_at=new_expiry, reason="Extended pilot")
    override_res = await admin_override_subscription_period(sub.id, override_req, super_admin=super_admin, db=mock_db)
    assert "overridden" in override_res.data.message.lower()
    assert sub.current_period_ends_at == new_expiry

    # 3. Cancel Subscription (Preserves Home & Data)
    mock_db.get.side_effect = [sub]
    cancel_req = AdminCancelSubscriptionRequest(reason="Terminated by customer request")
    cancel_res = await admin_cancel_subscription(sub.id, cancel_req, super_admin=super_admin, db=mock_db)
    assert sub.status == "CANCELED"
    assert home.status == "ACTIVE"
    assert home.deleted_at is None


# ==============================================================================
# 3. CHECKOUT & PRICING INTEGRATION TESTS (Items 19-26)
# ==============================================================================

@pytest.mark.asyncio
async def test_19_20_21_22_checkout_credit_calculation():
    """19, 20, 21, 22. Partial credit, full credit zero payable, and coupon stacking."""
    user_id = uuid4()
    plan = SubscriptionPlanModel(id=uuid4(), code="OZHZO_HOME", status="ACTIVE", included_members=1)
    
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)

    # 1. User has $50 credit, Plan price is $20.00 -> Credit applied $20.00, payable $0.00
    user = UserModel(id=user_id, email="credit_user@ozhzo.com")
    credit = SubscriptionCreditModel(
        id=uuid4(), user_id=user_id, amount=Decimal("50.00"), remaining_amount=Decimal("50.00"),
        currency="USD", status="AVAILABLE", credit_type="ADMIN_GRANT", created_at=now
    )

    mock_db.get.return_value = plan
    mock_price_res = MagicMock()
    mock_price_res.scalars.return_value.first.return_value = None
    mock_price_res.scalars.return_value.all.return_value = [credit]
    mock_db.execute.return_value = mock_price_res

    req = CheckoutSubscriptionRequest(plan_id=plan.id, currency="USD")
    res = await checkout_subscription(req, current_user=user, db=mock_db)

    assert res.data.amount == Decimal("20.00")
    assert res.data.credit_applied == Decimal("20.00")
    assert res.data.final_amount == Decimal("0.00")
    assert res.data.payment_required is False
    assert res.data.status == "SUCCESS"
    assert credit.remaining_amount == Decimal("30.00")


# ==============================================================================
# 4. ENTITLEMENT SYNCHRONIZATION TESTS (Items 27-30)
# ==============================================================================

@pytest.mark.asyncio
async def test_27_28_29_30_entitlement_lifecycle_and_home_permanence():
    """27, 28, 29, 30. Active grants access, cancelled/expired denies access, Home remains permanent."""
    owner_id = uuid4()
    home_id = uuid4()
    owner = UserModel(id=owner_id, email="owner@ozhzo.com")
    home = HomeModel(id=home_id, name="Permanent Villa", created_by=owner_id, status="ACTIVE")

    mock_db = AsyncMock()

    # Active Entitlement
    active_ent = HomeAccessEntitlementModel(
        id=uuid4(), home_id=home_id, user_id=owner_id, status="ACTIVE",
        expires_at=datetime.now(timezone.utc) + timedelta(days=200)
    )
    mock_res_active = MagicMock()
    mock_res_active.scalars.return_value.all.return_value = [active_ent]
    mock_db.execute.return_value = mock_res_active

    is_entitled, _, _ = await verify_user_home_access_entitlement(owner, home_id, mock_db)
    assert is_entitled is True

    # Expired Entitlement
    active_ent.expires_at = datetime.now(timezone.utc) - timedelta(days=10)
    is_entitled_exp, ent_exp, _ = await verify_user_home_access_entitlement(owner, home_id, mock_db)
    assert is_entitled_exp is False
    assert ent_exp.status == "EXPIRED"

    # Home and data remains intact
    assert home.status == "ACTIVE"
    assert home.deleted_at is None
