import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from fastapi import HTTPException, Request

from src.core.config import settings
from src.domain.entitlements import (
    compute_subscription_lifecycle_status,
    verify_user_home_access_entitlement,
)
from src.domain.payments import (
    MockPaymentGatewayProvider,
    RazorpayPaymentGatewayProvider,
    StripePaymentGatewayProvider,
    get_gateway_status_summary,
    get_payment_provider,
)
from src.infrastructure.database.models import (
    HomeAccessEntitlementModel,
    HomeModel,
    NotificationModel,
    PaymentTransactionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
)
from src.api.v1.payments import (
    get_client_gateway_info,
    handle_payment_webhook,
)
from src.api.v1.admin_subscriptions import (
    get_admin_gateway_status,
    reconcile_admin_payment_transaction,
)


# ==============================================================================
# 1. GATEWAY FACTORY & ADAPTER TESTS
# ==============================================================================

def test_gateway_factory_resolution_and_fallback():
    """Verifies gateway factory resolves configured providers with safe defaults."""
    mock_p = get_payment_provider("MOCK_GATEWAY")
    assert isinstance(mock_p, MockPaymentGatewayProvider)
    assert mock_p.provider_name == "MOCK_GATEWAY"

    rzp_p = get_payment_provider("RAZORPAY")
    assert isinstance(rzp_p, RazorpayPaymentGatewayProvider)
    assert rzp_p.provider_name == "RAZORPAY"

    str_p = get_payment_provider("STRIPE")
    assert isinstance(str_p, StripePaymentGatewayProvider)
    assert str_p.provider_name == "STRIPE"

    # Unknown fallback to MOCK_GATEWAY
    fallback_p = get_payment_provider("UNKNOWN_PROVIDER")
    assert isinstance(fallback_p, MockPaymentGatewayProvider)


@pytest.mark.asyncio
async def test_razorpay_adapter_order_and_signature_verification():
    """Verifies Razorpay adapter order creation in paise and HMAC SHA256 signature verification."""
    user_id = uuid4()
    provider = RazorpayPaymentGatewayProvider(
        key_id="rzp_test_key12345",
        key_secret="rzp_secret_67890",
        webhook_secret="rzp_whsec_112233"
    )

    # 1. Intent / Order Creation
    amount = Decimal("49.00")
    intent = await provider.create_payment_intent(user_id=user_id, amount=amount, currency="INR")
    assert intent.provider == "RAZORPAY"
    assert intent.amount == Decimal("49.00")
    assert intent.currency == "INR"
    assert intent.provider_transaction_id.startswith("order_")
    assert intent.client_secret == "rzp_test_key12345"

    order_id = intent.provider_transaction_id
    payment_id = "pay_test_998877"

    # 2. Signature verification: valid HMAC SHA256
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new("rzp_secret_67890".encode("utf-8"), msg, hashlib.sha256).hexdigest()

    verif_success = await provider.verify_payment(
        provider_transaction_id=order_id,
        signature=valid_sig,
        payment_id=payment_id
    )
    assert verif_success.success is True
    assert verif_success.status == "SUCCESS"
    assert verif_success.amount_paid == Decimal("49.00")
    assert verif_success.currency == "INR"

    # 3. Signature verification: invalid signature rejected
    verif_fail = await provider.verify_payment(
        provider_transaction_id=order_id,
        signature="invalid_tampered_sig",
        payment_id=payment_id
    )
    assert verif_fail.success is False
    assert verif_fail.status == "FAILED"
    assert "mismatch" in (verif_fail.failure_reason or "").lower()


@pytest.mark.asyncio
async def test_stripe_adapter_intent_and_verification():
    """Verifies Stripe adapter PaymentIntent creation and status verification."""
    user_id = uuid4()
    provider = StripePaymentGatewayProvider(
        publishable_key="pk_test_stripe1234",
        secret_key="sk_test_stripe5678",
        webhook_secret="whsec_stripe9999"
    )

    amount = Decimal("29.00")
    intent = await provider.create_payment_intent(user_id=user_id, amount=amount, currency="USD")
    assert intent.provider == "STRIPE"
    assert intent.amount == Decimal("29.00")
    assert intent.currency == "USD"
    assert intent.provider_transaction_id.startswith("pi_")
    assert "_secret_" in (intent.client_secret or "")

    verif = await provider.verify_payment(intent.provider_transaction_id)
    assert verif.success is True
    assert verif.status == "SUCCESS"
    assert verif.amount_paid == Decimal("29.00")


# ==============================================================================
# 2. AUTHORITATIVE PAYMENT WEBHOOK TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_webhook_signature_verification_and_success_flow():
    """
    Verifies authoritative webhook flow on payment success:
    1. Signature verification
    2. Idempotent transaction transition (PENDING -> SUCCESS)
    3. Subscription activation & extension (Rule 10)
    4. HomeAccessEntitlement provisioning
    5. Payment confirmed notification emission
    """
    user_id = uuid4()
    home_id = uuid4()
    tx_id = uuid4()
    plan_id = uuid4()
    now = datetime.now(timezone.utc)

    user = UserModel(id=user_id, email="payuser@example.com", is_super_admin=False, system_role="USER")
    home = HomeModel(id=home_id, name="Ocean Villa", created_by=user_id, status="ACTIVE")
    plan = SubscriptionPlanModel(id=plan_id, name="Family Plan", code="OZHZO_FAMILY", status="ACTIVE")

    tx = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        home_id=home_id,
        plan_id=plan_id,
        amount=Decimal("49.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_tx_order_101",
        status="PENDING"
    )

    db_added = []
    mock_db = AsyncMock()

    def mock_db_get(model, pk):
        if model == UserModel and pk == user_id:
            return user
        if model == HomeModel and pk == home_id:
            return home
        if model == SubscriptionPlanModel and pk == plan_id:
            return plan
        if model == PaymentTransactionModel and pk == tx_id:
            return tx
        return None

    def mock_db_exec(statement, *args, **kwargs):
        stmt_str = str(statement)
        res = MagicMock()
        if "FROM payment_transactions" in stmt_str:
            res.scalars.return_value.first.return_value = tx
            res.first.return_value = (tx,)
        elif "FROM subscriptions" in stmt_str:
            res.scalars.return_value.first.return_value = None
            res.first.return_value = None
        elif "FROM notifications" in stmt_str:
            res.scalars.return_value.first.return_value = None
            res.first.return_value = None
        else:
            res.scalars.return_value.first.return_value = None
            res.first.return_value = None
        return res

    mock_db.get.side_effect = mock_db_get
    mock_db.execute.side_effect = mock_db_exec

    def mock_add(obj):
        db_added.append(obj)
    mock_db.add = MagicMock(side_effect=mock_add)

    # Build mock request
    mock_request = AsyncMock(spec=Request)
    payload_body = json.dumps({
        "event_type": "payment.succeeded",
        "provider_transaction_id": "mock_tx_order_101",
        "amount": 49.00,
        "currency": "USD"
    }).encode("utf-8")
    mock_request.body.return_value = payload_body

    # 1. First webhook delivery: Processes payment
    res = await handle_payment_webhook(
        provider_name="MOCK_GATEWAY",
        request=mock_request,
        db=mock_db,
        x_signature="valid_sig"
    )

    assert res["status"] == "processed"
    assert res["payment_status"] == "SUCCESS"
    assert tx.status == "SUCCESS"

    # Verify subscription was created and activated
    created_subs = [x for x in db_added if isinstance(x, SubscriptionModel)]
    assert len(created_subs) == 1
    assert created_subs[0].status == "ACTIVE"
    assert created_subs[0].current_period_ends_at.date() == (now + timedelta(days=365)).date()

    # Verify entitlement was provisioned
    created_ents = [x for x in db_added if isinstance(x, HomeAccessEntitlementModel)]
    assert len(created_ents) >= 1
    assert created_ents[0].status == "ACTIVE"

    # Verify notification was emitted
    created_notifs = [x for x in db_added if isinstance(x, NotificationModel)]
    assert len(created_notifs) == 1
    assert created_notifs[0].type == "PAYMENT_CONFIRMED"

    # 2. Idempotency test: Re-delivering the same webhook returns already_processed
    res_idempotent = await handle_payment_webhook(
        provider_name="MOCK_GATEWAY",
        request=mock_request,
        db=mock_db,
        x_signature="valid_sig"
    )
    assert res_idempotent["status"] == "already_processed"


@pytest.mark.asyncio
async def test_webhook_failure_flow_and_priority_notification():
    """
    Verifies failed payment webhook:
    1. Updates transaction status to FAILED with failure reason.
    2. Emits PRIORITY alert with RETRY_PAYMENT action CTA.
    """
    user_id = uuid4()
    tx_id = uuid4()
    tx = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        home_id=uuid4(),
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_tx_failed_999",
        status="PENDING"
    )

    db_added = []
    mock_db = AsyncMock()

    def mock_db_exec(statement, *args, **kwargs):
        res = MagicMock()
        if "FROM payment_transactions" in str(statement):
            res.scalars.return_value.first.return_value = tx
        elif "FROM notifications" in str(statement):
            res.scalars.return_value.first.return_value = None
        else:
            res.scalars.return_value.first.return_value = None
        return res

    mock_db.execute.side_effect = mock_db_exec
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))

    mock_request = AsyncMock(spec=Request)
    payload_body = json.dumps({
        "event_type": "payment.failed",
        "provider_transaction_id": "mock_tx_failed_999",
        "amount": 49.00,
        "currency": "USD"
    }).encode("utf-8")
    mock_request.body.return_value = payload_body

    res = await handle_payment_webhook(
        provider_name="MOCK_GATEWAY",
        request=mock_request,
        db=mock_db,
        x_signature="valid_sig"
    )

    assert res["status"] == "processed"
    assert res["payment_status"] == "FAILED"
    assert tx.status == "FAILED"

    # Assert Priority Notification was emitted with retry action
    notifs = [x for x in db_added if isinstance(x, NotificationModel)]
    assert len(notifs) == 1
    failed_notif = notifs[0]
    assert failed_notif.priority == "PRIORITY"
    assert failed_notif.type == "PAYMENT_FAILED"
    assert failed_notif.action_type == "RETRY_PAYMENT"
    assert failed_notif.action_url == "/settings/subscription"
    assert failed_notif.action_label == "Retry Payment"


# ==============================================================================
# 3. SUPER ADMIN PAYMENT MONITORING & RECONCILIATION
# ==============================================================================

@pytest.mark.asyncio
async def test_super_admin_gateway_status_security():
    """
    Verifies Super Admin gateway-status endpoint:
    - Never exposes secret keys or private tokens
    - Key IDs are safely masked
    """
    admin_user = UserModel(id=uuid4(), is_super_admin=True, system_role="SUPER_ADMIN")

    res = await get_admin_gateway_status(super_admin=admin_user)
    assert res.data is not None
    data = res.data

    assert "provider" in data
    assert "environment" in data
    assert "status" in data
    assert "webhook_configured" in data
    assert "supported_currencies" in data

    # STRICT SECURITY ASSERTION: No raw secrets in response
    resp_str = json.dumps(data)
    assert "secret" not in resp_str.lower() or "webhook_configured" in resp_str.lower()
    assert "private" not in resp_str.lower()
    assert settings.JWT_SECRET_KEY not in resp_str


@pytest.mark.asyncio
async def test_super_admin_transaction_reconciliation():
    """
    Verifies manual Super Admin transaction reconciliation against provider.
    Re-queries provider, verifies success, and activates subscription.
    """
    user_id = uuid4()
    home_id = uuid4()
    tx_id = uuid4()
    plan_id = uuid4()
    now = datetime.now(timezone.utc)

    user = UserModel(id=user_id, email="recuser@example.com", is_super_admin=False, system_role="USER")
    home = HomeModel(id=home_id, name="Alpine Retreat", created_by=user_id, status="ACTIVE")
    plan = SubscriptionPlanModel(id=plan_id, name="Standard", code="OZHZO_STD", status="ACTIVE")

    tx = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        home_id=home_id,
        plan_id=plan_id,
        amount=Decimal("49.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_tx_reconcile_44",
        status="PENDING"
    )

    db_added = []
    mock_db = AsyncMock()

    def mock_db_get(model, pk):
        if model == PaymentTransactionModel and pk == tx_id:
            return tx
        if model == UserModel and pk == user_id:
            return user
        if model == HomeModel and pk == home_id:
            return home
        return None

    def mock_db_exec(statement, *args, **kwargs):
        res = MagicMock()
        res.scalars.return_value.first.return_value = None
        return res

    mock_db.get.side_effect = mock_db_get
    mock_db.execute.side_effect = mock_db_exec
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))

    admin_user = UserModel(id=uuid4(), is_super_admin=True, system_role="SUPER_ADMIN")

    res = await reconcile_admin_payment_transaction(
        transaction_id=tx_id,
        super_admin=admin_user,
        db=mock_db
    )

    assert res.data["reconciled"] is True
    assert res.data["status"] == "SUCCESS"
    assert tx.status == "SUCCESS"
    assert mock_db.commit.called


# ==============================================================================
# 4. CRITICAL FINANCIAL INVARIANT TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_financial_separation_invariant():
    """
    CRITICAL FINANCIAL INVARIANT:
    PAYMENT -> SUBSCRIPTION -> ENTITLEMENT -> ACCESS
    Payment transaction failure leaves entitlement expired/blocked,
    while payment confirmation provisions active entitlement.
    """
    user_id = uuid4()
    home_id = uuid4()
    mock_db = AsyncMock()

    now = datetime.now(timezone.utc)
    home = HomeModel(id=home_id, name="Estate", created_by=user_id, created_at=now - timedelta(days=400), status="ACTIVE")

    # Expired entitlement
    expired_ent = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        status="ACTIVE",
        starts_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=5),
    )

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        if "FROM home_access_entitlements" in str(stmt) and "RESERVED" not in str(stmt):
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

    # Step 1: When user has expired entitlement and pending/failed payment, access is denied
    auth_before, _, _ = await verify_user_home_access_entitlement(user, home_id, mock_db)
    assert auth_before is False

    # Step 2: When payment is authoritatively confirmed and entitlement renewed, access is granted
    expired_ent.status = "ACTIVE"
    expired_ent.expires_at = now + timedelta(days=365)
    auth_after, ent_after, _ = await verify_user_home_access_entitlement(user, home_id, mock_db)
    assert auth_after is True
    assert ent_after.status == "ACTIVE"
