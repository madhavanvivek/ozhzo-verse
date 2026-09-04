import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from src.api.dependencies import require_super_admin
from src.domain.entitlements import (
    compute_subscription_lifecycle_status,
    consume_user_credits,
    get_user_credit_balance,
    grant_user_credit,
    process_subscription_lifecycle_transitions,
    provision_first_year_free_entitlement,
    provision_paid_home_entitlement,
    verify_user_home_access_entitlement,
)
from src.infrastructure.database.models import (
    HomeAccessEntitlementModel,
    HomeModel,
    HomeMemberModel,
    NotificationModel,
    PaymentTransactionModel,
    SubscriptionCreditModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
)
from src.schemas.subscription import (
    AdminGrantSubscriptionRequest,
    CheckoutSubscriptionRequest,
    ConfirmPaymentRequest,
)
from src.api.v1.admin_subscriptions import (
    admin_grant_subscription,
    admin_process_subscription_lifecycle,
)
from src.api.v1.subscriptions import (
    checkout_subscription,
    confirm_payment,
    get_my_subscription_entitlements,
)
from src.services.notification_service import (
    InAppChannelHandler,
    NotificationPayload,
    NotificationService,
)


# ==============================================================================
# 1. CORE BUSINESS RULES (Rules 1-6)
# ==============================================================================

@pytest.mark.asyncio
async def test_rule1_home_permanence_on_subscription_expiry():
    """
    Rule 1: HOME NEVER EXPIRES.
    Subscription expiry must NEVER delete, archive, or modify the Home or household data.
    Only the affected person's access entitlement changes.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_db = AsyncMock()

    now = datetime.now(timezone.utc)
    # Home record exists and was created > 365 days ago (so 1st year free is expired)
    home = HomeModel(
        id=home_id,
        name="The Family Villa",
        created_by=user_id,
        created_at=now - timedelta(days=400),
        status="ACTIVE",
        deleted_at=None
    )
    # Expired entitlement
    expired_ent = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        entitlement_type="PAID_SEAT",
        status="ACTIVE",
        starts_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=35),  # expired 35 days ago
    )

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM home_access_entitlements" in stmt_str and "status = :status_1" not in stmt_str:
            res.scalars.return_value.all.return_value = [expired_ent]
            res.all.return_value = [expired_ent]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
            res.all.return_value = []
            res.first.return_value = None
            res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute.side_effect = mock_exec
    mock_db.get.return_value = home

    user = UserModel(id=user_id, is_super_admin=False, system_role="USER")
    authorized, ent, reason = await verify_user_home_access_entitlement(user, home_id, mock_db)

    # Access is denied for the user
    assert authorized is False
    assert ent.status == "EXPIRED"

    # Crucial Invariant: Home status and household data remain 100% untouched
    assert home.status == "ACTIVE"
    assert home.deleted_at is None
    assert home.name == "The Family Villa"


@pytest.mark.asyncio
async def test_rule2_first_home_free_period_transitions_to_expired():
    """
    Rule 2: FIRST HOME FREE PERIOD: First year is free.
    After 365 days, access requires a valid paid subscription.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_db = AsyncMock()

    now = datetime.now(timezone.utc)
    home = HomeModel(
        id=home_id,
        name="First Home",
        created_by=user_id,
        created_at=now - timedelta(days=370),  # Created 370 days ago
        status="ACTIVE",
        deleted_at=None
    )

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        res.scalars.return_value.first.return_value = None
        res.all.return_value = []
        res.first.return_value = None
        res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute.side_effect = mock_exec
    mock_db.get.return_value = home

    user = UserModel(id=user_id, free_home_consumed=True, is_super_admin=False, system_role="USER")
    authorized, ent, reason = await verify_user_home_access_entitlement(user, home_id, mock_db)

    # Access is denied because > 365 days elapsed since home creation and no paid sub
    assert authorized is False
    assert "expired" in reason.lower()


@pytest.mark.asyncio
async def test_rule4_per_person_access_entitlement_isolation():
    """
    Rule 4: Every person needs their own access.
    Member A (expired) is denied access, while Member B (active) retains full access.
    Neither affects the other or the Home.
    """
    home_id = uuid4()
    user_a_id = uuid4()
    user_b_id = uuid4()
    now = datetime.now(timezone.utc)

    # Expired entitlement for User A
    ent_a = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_a_id,
        status="ACTIVE",
        starts_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=10),
    )
    # Active entitlement for User B
    ent_b = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_b_id,
        status="ACTIVE",
        starts_at=now - timedelta(days=100),
        expires_at=now + timedelta(days=265),
    )

    db_a = AsyncMock()
    def mock_a(stmt, *args, **kwargs):
        res = MagicMock()
        if "FROM home_access_entitlements" in str(stmt) and "RESERVED" not in str(stmt):
            res.scalars.return_value.all.return_value = [ent_a]
            res.all.return_value = [ent_a]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
            res.all.return_value = []
            res.first.return_value = None
            res.scalar_one_or_none.return_value = None
        return res
    db_a.execute.side_effect = mock_a

    db_b = AsyncMock()
    def mock_b(stmt, *args, **kwargs):
        res = MagicMock()
        if "FROM home_access_entitlements" in str(stmt) and "RESERVED" not in str(stmt):
            res.scalars.return_value.all.return_value = [ent_b]
            res.all.return_value = [ent_b]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
            res.all.return_value = []
            res.first.return_value = None
            res.scalar_one_or_none.return_value = None
        return res
    db_b.execute.side_effect = mock_b

    user_a = UserModel(id=user_a_id, is_super_admin=False, system_role="USER")
    user_b = UserModel(id=user_b_id, is_super_admin=False, system_role="USER")

    auth_a, _, _ = await verify_user_home_access_entitlement(user_a, home_id, db_a)
    auth_b, _, _ = await verify_user_home_access_entitlement(user_b, home_id, db_b)

    assert auth_a is False  # User A blocked
    assert auth_b is True   # User B allowed


@pytest.mark.asyncio
async def test_rule5_home_admin_does_not_bypass_subscription():
    """
    Rule 5: Home Admin does NOT bypass subscription requirements.
    """
    home_id = uuid4()
    admin_user_id = uuid4()
    now = datetime.now(timezone.utc)

    ent_admin = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=admin_user_id,
        status="ACTIVE",
        starts_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=1),  # Expired yesterday
    )

    mock_db = AsyncMock()
    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        if "FROM home_access_entitlements" in str(stmt) and "RESERVED" not in str(stmt):
            res.scalars.return_value.all.return_value = [ent_admin]
            res.all.return_value = [ent_admin]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
            res.all.return_value = []
            res.first.return_value = None
            res.scalar_one_or_none.return_value = None
        return res
    mock_db.execute.side_effect = mock_exec

    # User has household role ADMIN but is NOT platform Super Admin
    home_admin_user = UserModel(id=admin_user_id, is_super_admin=False, system_role="USER")
    auth, _, reason = await verify_user_home_access_entitlement(home_admin_user, home_id, mock_db)

    assert auth is False
    assert "expired" in reason.lower()


@pytest.mark.asyncio
async def test_rule6_super_admin_separate_platform_access():
    """
    Rule 6: Super Admin platform access remains completely separate and exempt.
    """
    home_id = uuid4()
    super_admin_id = uuid4()
    mock_db = AsyncMock()

    super_admin = UserModel(id=super_admin_id, is_super_admin=True, system_role="SUPER_ADMIN")
    auth, _, reason = await verify_user_home_access_entitlement(super_admin, home_id, mock_db)

    assert auth is True
    assert "Super Admin" in reason


# ==============================================================================
# 2. DETERMINISTIC LIFECYCLE & WARNING WINDOW (Rules 3, 4, 5, 7)
# ==============================================================================

def test_lifecycle_status_computation():
    """Tests deterministic compute_subscription_lifecycle_status across all states."""
    now = datetime.now(timezone.utc)

    # 1. ACTIVE (ends in 30 days)
    sub_active = SubscriptionModel(
        status="ACTIVE",
        current_period_ends_at=now + timedelta(days=30)
    )
    assert compute_subscription_lifecycle_status(sub_active, now, warning_days=7) == "ACTIVE"

    # 2. EXPIRING (ends in 5 days, default warning=7)
    sub_expiring = SubscriptionModel(
        status="ACTIVE",
        current_period_ends_at=now + timedelta(days=5)
    )
    assert compute_subscription_lifecycle_status(sub_expiring, now, warning_days=7) == "EXPIRING"

    # 3. EXPIRED (ended 2 days ago)
    sub_expired = SubscriptionModel(
        status="ACTIVE",
        current_period_ends_at=now - timedelta(days=2)
    )
    assert compute_subscription_lifecycle_status(sub_expired, now, warning_days=7) == "EXPIRED"

    # 4. CANCELLED / FAILED / PENDING preserve their status
    sub_cancelled = SubscriptionModel(
        status="CANCELLED",
        current_period_ends_at=now + timedelta(days=10)
    )
    assert compute_subscription_lifecycle_status(sub_cancelled, now) == "CANCELLED"


def test_configurable_warning_windows():
    """Tests configurable warning thresholds (e.g. 14 days, 30 days)."""
    now = datetime.now(timezone.utc)
    sub = SubscriptionModel(
        status="ACTIVE",
        current_period_ends_at=now + timedelta(days=10)
    )

    # With 7-day warning, 10 days left is still ACTIVE
    assert compute_subscription_lifecycle_status(sub, now, warning_days=7) == "ACTIVE"

    # With 14-day warning, 10 days left is EXPIRING
    assert compute_subscription_lifecycle_status(sub, now, warning_days=14) == "EXPIRING"

    # With 30-day warning, 10 days left is EXPIRING
    assert compute_subscription_lifecycle_status(sub, now, warning_days=30) == "EXPIRING"


# ==============================================================================
# 3. IDEMPOTENT EXPIRY PROCESSING & DEDUPLICATION (Rules 8, 14, 15)
# ==============================================================================

@pytest.mark.asyncio
async def test_idempotent_expiry_processor_and_deduplication():
    """
    Rule 8: Running expiry processing 1x or 10x produces the same state and exactly 1 notification.
    """
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    sub_id = uuid4()
    plan = SubscriptionPlanModel(id=uuid4(), name="Household Standard", code="OZHZO_HOME")

    # Subscription that expired yesterday
    sub = SubscriptionModel(
        id=sub_id,
        user_id=user_id,
        home_id=uuid4(),
        status="ACTIVE",
        current_period_ends_at=now - timedelta(days=1),
        plan=plan
    )

    db_notifications = []
    mock_db = AsyncMock()

    def mock_execute_side_effect(statement, *args, **kwargs):
        stmt_str = str(statement)
        mock_result = MagicMock()
        if "FROM subscriptions" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [sub] if sub.status != "EXPIRED" else []
            mock_result.all.return_value = [sub] if sub.status != "EXPIRED" else []
        elif "FROM home_access_entitlements" in stmt_str:
            mock_result.scalars.return_value.all.return_value = []
            mock_result.all.return_value = []
        elif "FROM notifications" in stmt_str and "dedup_key" in stmt_str:
            matching = [n for n in db_notifications if getattr(n, "dedup_key", None) is not None]
            mock_result.scalars.return_value.first.return_value = matching[0] if matching else None
            mock_result.scalar_one_or_none.return_value = matching[0] if matching else None
            mock_result.first.return_value = (matching[0].id,) if matching else None
        else:
            mock_result.scalars.return_value.all.return_value = []
            mock_result.scalars.return_value.first.return_value = None
            mock_result.all.return_value = []
            res_first = None
            mock_result.first.return_value = res_first
            mock_result.scalar_one_or_none.return_value = res_first
        return mock_result

    mock_db.execute.side_effect = mock_execute_side_effect

    def mock_add(obj):
        if isinstance(obj, NotificationModel):
            db_notifications.append(obj)

    mock_db.add = MagicMock(side_effect=mock_add)

    # Pass 1: Should expire subscription and create 1 notification
    metrics_1 = await process_subscription_lifecycle_transitions(mock_db, warning_days=7, now=now)
    assert metrics_1["expired_subscriptions"] == 1
    assert metrics_1["notifications_created"] == 1
    assert sub.status == "EXPIRED"
    assert len(db_notifications) == 1
    assert db_notifications[0].priority == "PRIORITY"
    assert db_notifications[0].action_type == "RENEW"
    assert db_notifications[0].action_url == "/settings/subscription"
    assert db_notifications[0].action_label == "Renew Now"

    # Pass 2 (Idempotency test): Sub is now EXPIRED, should create 0 new notifications
    metrics_2 = await process_subscription_lifecycle_transitions(mock_db, warning_days=7, now=now)
    assert metrics_2["notifications_created"] == 0
    assert len(db_notifications) == 1  # Still exactly 1 notification


# ==============================================================================
# 4. RENEWAL EXTENSION MECHANICS (Rules 9, 10, 11, 12)
# ==============================================================================

@pytest.mark.asyncio
async def test_rule10_active_subscription_renewal_extends_period():
    """
    Rule 10: Active/expiring subscription renewed -> extends from current_period_ends_at + 1 year.
    (Does not forfeit remaining paid days).
    """
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    home_id = uuid4()
    current_expiry = now + timedelta(days=25)  # 25 days remaining

    # Existing active subscription
    existing_sub = SubscriptionModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        status="ACTIVE",
        current_period_starts_at=now - timedelta(days=340),
        current_period_ends_at=current_expiry,
        paid_member_seats=0
    )

    plan = SubscriptionPlanModel(id=uuid4(), name="Household Standard", code="OZHZO_HOME", status="ACTIVE")

    mock_db = AsyncMock()

    def mock_sub_execute(statement, *args, **kwargs):
        stmt_str = str(statement)
        mock_result = MagicMock()
        if "FROM subscriptions" in stmt_str:
            mock_result.scalars.return_value.first.return_value = existing_sub
            mock_result.scalar_one_or_none.return_value = existing_sub
            mock_result.first.return_value = existing_sub
        elif "FROM home_access_entitlements" in stmt_str:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalar_one_or_none.return_value = None
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = mock_sub_execute

    tx = PaymentTransactionModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        plan_id=plan.id,
        amount=Decimal("49.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        status="PENDING",
        provider="MOCK"
    )
    mock_db.get.side_effect = lambda model, pk: tx if model == PaymentTransactionModel else plan

    user = UserModel(id=user_id, is_super_admin=False, system_role="USER")

    # Confirm payment
    conf_req = ConfirmPaymentRequest(
        transaction_id=tx.id,
        provider_transaction_id="mock_tx_123",
        signature="mock_sig_123"
    )
    res = await confirm_payment(payload=conf_req, current_user=user, db=mock_db)
    assert res.data.success is True

    # Expected new expiry: current_expiry + 365 days
    expected_expiry = current_expiry + timedelta(days=365)
    assert existing_sub.current_period_ends_at.date() == expected_expiry.date()
    assert existing_sub.status == "ACTIVE"


@pytest.mark.asyncio
async def test_rule10_expired_subscription_renewal_starts_from_today():
    """
    Rule 10: Expired subscription renewed -> starts from today (now + 1 year).
    """
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    home_id = uuid4()

    # Expired subscription (ended 10 days ago)
    expired_sub = SubscriptionModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        status="EXPIRED",
        current_period_starts_at=now - timedelta(days=375),
        current_period_ends_at=now - timedelta(days=10),
        paid_member_seats=0
    )

    plan = SubscriptionPlanModel(id=uuid4(), name="Household Standard", code="OZHZO_HOME", status="ACTIVE")
    tx = PaymentTransactionModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        plan_id=plan.id,
        amount=Decimal("49.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        status="PENDING",
        provider="MOCK"
    )

    mock_db = AsyncMock()

    def mock_sub_execute(statement, *args, **kwargs):
        stmt_str = str(statement)
        mock_result = MagicMock()
        if "FROM subscriptions" in stmt_str:
            mock_result.scalars.return_value.first.return_value = expired_sub
            mock_result.scalar_one_or_none.return_value = expired_sub
            mock_result.first.return_value = expired_sub
        elif "FROM home_access_entitlements" in stmt_str:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalar_one_or_none.return_value = None
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = mock_sub_execute
    mock_db.get.side_effect = lambda model, pk: tx if model == PaymentTransactionModel else plan

    user = UserModel(id=user_id, is_super_admin=False, system_role="USER")
    conf_req = ConfirmPaymentRequest(
        transaction_id=tx.id,
        provider_transaction_id="mock_tx_456",
        signature="mock_sig_456"
    )
    res = await confirm_payment(payload=conf_req, current_user=user, db=mock_db)
    assert res.data.success is True

    # Expected new expiry: now + 365 days
    expected_expiry = now + timedelta(days=365)
    assert expired_sub.current_period_ends_at.date() == expected_expiry.date()
    assert expired_sub.status == "ACTIVE"


# ==============================================================================
# 5. SUPER ADMIN LIFECYCLE PROCESSING API ENDPOINT (Rule 16)
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_process_subscription_lifecycle_endpoint():
    """
    Super Admin endpoint POST /admin/subscriptions/process-lifecycle triggers lifecycle transitions.
    """
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.all.return_value = []
    mock_res.scalars.return_value.first.return_value = None
    mock_res.first.return_value = None
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    admin_user = UserModel(id=uuid4(), is_super_admin=True, system_role="SUPER_ADMIN")

    res = await admin_process_subscription_lifecycle(
        warning_days=7,
        super_admin=admin_user,
        db=mock_db
    )

    assert res.data is not None
    assert "expired_subscriptions" in res.data
    assert "expiring_subscriptions" in res.data
    assert "notifications_created" in res.data
    assert "evaluated_at" in res.data
    assert mock_db.commit.called
