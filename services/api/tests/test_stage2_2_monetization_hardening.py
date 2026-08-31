import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from src.api.v1.subscriptions import (
    checkout_subscription,
    confirm_payment,
    handle_payment_webhook,
)
from src.domain.payments import (
    MockPaymentGatewayProvider,
    PaymentIntentResult,
    PaymentVerificationResult,
    RefundResult,
    get_payment_provider,
)
from src.infrastructure.database.models import (
    CouponModel,
    HomeModel,
    PaymentTransactionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel,
)
from src.schemas.subscription import (
    CheckoutSubscriptionRequest,
    ConfirmPaymentRequest,
)


@pytest.mark.asyncio
async def test_01_mock_provider_deterministic_intent_and_exact_amount_verification():
    """Verify MockPaymentGatewayProvider registers intent and preserves exact amount/currency."""
    provider = MockPaymentGatewayProvider()
    user_id = uuid4()

    intent = await provider.create_payment_intent(
        user_id=user_id,
        amount=Decimal("49.00"),
        currency="USD",
        metadata={"plan": "Pro"},
    )

    assert intent.provider == "MOCK_GATEWAY"
    assert intent.amount == Decimal("49.00")
    assert intent.currency == "USD"
    assert intent.status == "PENDING"
    assert intent.provider_transaction_id.startswith("mock_tx_")

    # Verify normal payment returns exact amount and currency
    res = await provider.verify_payment(intent.provider_transaction_id)
    assert res.success is True
    assert res.amount_paid == Decimal("49.00")
    assert res.currency == "USD"
    assert res.status == "SUCCESS"


@pytest.mark.asyncio
async def test_02_payment_verification_amount_mismatch_rejected():
    """Verify payment confirmation rejects amount mismatch (e.g. expected $49, received $10)."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="pay_mismatch@ozhzo.com", mobile_verified=True, free_home_consumed=True)

    transaction_id = uuid4()
    transaction = PaymentTransactionModel(
        id=transaction_id,
        user_id=user_id,
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("0.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_mismatch_amount_123",
        status="PENDING",
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = transaction

    req = ConfirmPaymentRequest(
        transaction_id=transaction_id,
        provider_transaction_id="mock_mismatch_amount_123",
    )

    with pytest.raises(HTTPException) as exc_info:
        await confirm_payment(req, current_user=user, db=mock_db)

    assert exc_info.value.status_code == 400
    assert "Amount mismatch" in exc_info.value.detail
    assert transaction.status == "FAILED"


@pytest.mark.asyncio
async def test_03_payment_verification_currency_mismatch_rejected():
    """Verify payment confirmation rejects currency mismatch (e.g. expected USD, received EUR)."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="curr_mismatch@ozhzo.com", mobile_verified=True, free_home_consumed=True)

    transaction_id = uuid4()
    transaction = PaymentTransactionModel(
        id=transaction_id,
        user_id=user_id,
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("0.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_mismatch_currency_123",
        status="PENDING",
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = transaction

    req = ConfirmPaymentRequest(
        transaction_id=transaction_id,
        provider_transaction_id="mock_mismatch_currency_123",
    )

    with pytest.raises(HTTPException) as exc_info:
        await confirm_payment(req, current_user=user, db=mock_db)

    assert exc_info.value.status_code == 400
    assert "Currency mismatch" in exc_info.value.detail
    assert transaction.status == "FAILED"


@pytest.mark.asyncio
async def test_04_failed_payment_declined_card():
    """Verify card decline or failure trigger does not activate subscription."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="decline@ozhzo.com", mobile_verified=True, free_home_consumed=True)

    transaction_id = uuid4()
    transaction = PaymentTransactionModel(
        id=transaction_id,
        user_id=user_id,
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("0.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_fail_declined",
        status="PENDING",
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = transaction

    req = ConfirmPaymentRequest(
        transaction_id=transaction_id,
        provider_transaction_id="mock_fail_declined",
    )

    with pytest.raises(HTTPException) as exc_info:
        await confirm_payment(req, current_user=user, db=mock_db)

    assert exc_info.value.status_code == 400
    assert transaction.status == "FAILED"
    assert transaction.subscription_id is None


@pytest.mark.asyncio
async def test_05_duplicate_confirmation_idempotent():
    """Verify duplicate confirm_payment calls are safely idempotent."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="idempotent@ozhzo.com", mobile_verified=True)

    existing_sub_id = uuid4()
    transaction_id = uuid4()
    transaction = PaymentTransactionModel(
        id=transaction_id,
        user_id=user_id,
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("0.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_tx_settled",
        subscription_id=existing_sub_id,
        status="SUCCESS",
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = transaction

    req = ConfirmPaymentRequest(
        transaction_id=transaction_id,
        provider_transaction_id="mock_tx_settled",
    )

    res = await confirm_payment(req, current_user=user, db=mock_db)
    assert res.data.success is True
    assert res.data.status == "ACTIVE"
    assert res.data.subscription_id == existing_sub_id


@pytest.mark.asyncio
async def test_06_100_percent_coupon_zero_payable():
    """Verify 100% coupon activates subscription directly without external payment requirement."""
    user_id = uuid4()
    user = UserModel(id=user_id, email="free_coupon@ozhzo.com", mobile_verified=True, free_home_consumed=False)

    transaction_id = uuid4()
    transaction = PaymentTransactionModel(
        id=transaction_id,
        user_id=user_id,
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("49.00"),
        final_amount=Decimal("0.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_tx_zero_amount",
        status="PENDING",
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = transaction
    mock_res_empty = MagicMock()
    mock_res_empty.scalar_one_or_none.return_value = None
    mock_res_empty.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res_empty

    req = ConfirmPaymentRequest(
        transaction_id=transaction_id,
        provider_transaction_id="mock_tx_zero_amount",
    )

    res = await confirm_payment(req, current_user=user, db=mock_db)
    assert res.data.success is True
    assert res.data.status == "ACTIVE"
    assert transaction.status == "SUCCESS"
    assert user.free_home_consumed is True


@pytest.mark.asyncio
async def test_07_payment_webhook_lifecycle_and_security():
    """Verify webhook signature checking, amount validation, duplicate idempotency, and refund events."""
    tx_id = uuid4()
    user_id = uuid4()
    sub_id = uuid4()

    transaction = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        plan_id=uuid4(),
        amount=Decimal("49.00"),
        discount_amount=Decimal("0.00"),
        final_amount=Decimal("49.00"),
        currency="USD",
        provider="MOCK_GATEWAY",
        provider_transaction_id="mock_webhook_tx_777",
        subscription_id=None,
        status="PENDING",
    )

    subscription = SubscriptionModel(
        id=sub_id,
        home_id=uuid4(),
        user_id=user_id,
        plan_id=uuid4(),
        status="ACTIVE",
    )

    mock_db = AsyncMock()
    mock_tx_res = MagicMock()
    mock_tx_res.scalar_one_or_none.return_value = transaction
    mock_db.execute.return_value = mock_tx_res
    mock_db.get.side_effect = lambda model, obj_id: subscription if model == SubscriptionModel else None

    # 7a. Webhook with invalid signature is rejected (401)
    mock_req_invalid = AsyncMock()
    mock_req_invalid.headers = {"x-webhook-signature": "invalid_signature"}
    mock_req_invalid.json.return_value = {
        "event_type": "payment.succeeded",
        "provider_transaction_id": "mock_webhook_tx_777",
        "amount": 49.00,
        "currency": "USD",
    }

    with pytest.raises(HTTPException) as exc_info:
        await handle_payment_webhook("MOCK_GATEWAY", mock_req_invalid, db=mock_db)
    assert exc_info.value.status_code == 401

    # 7b. Webhook with valid signature and amount match succeeds
    mock_req_valid = AsyncMock()
    mock_req_valid.headers = {"x-webhook-signature": "valid_sig_123"}
    mock_req_valid.json.return_value = {
        "event_type": "payment.succeeded",
        "provider_transaction_id": "mock_webhook_tx_777",
        "amount": 49.00,
        "currency": "USD",
    }

    res_valid = await handle_payment_webhook("MOCK_GATEWAY", mock_req_valid, db=mock_db)
    assert res_valid["status"] == "processed"
    assert transaction.status == "SUCCESS"

    # 7c. Duplicate webhook event is idempotent (returns processed without duplicating subscription)
    res_dup = await handle_payment_webhook("MOCK_GATEWAY", mock_req_valid, db=mock_db)
    assert res_dup["status"] == "processed"
    assert "already settled" in res_dup["message"]

    # 7d. Refund webhook cancels subscription and marks transaction REFUNDED
    mock_req_refund = AsyncMock()
    mock_req_refund.headers = {"x-webhook-signature": "valid_sig_123"}
    mock_req_refund.json.return_value = {
        "event_type": "payment.refunded",
        "provider_transaction_id": "mock_webhook_tx_777",
        "amount": 49.00,
        "currency": "USD",
    }

    res_refund = await handle_payment_webhook("MOCK_GATEWAY", mock_req_refund, db=mock_db)
    assert res_refund["status"] == "processed"
    assert res_refund["action"] == "refund_applied"
    assert transaction.status == "REFUNDED"
    assert subscription.status == "CANCELED"
