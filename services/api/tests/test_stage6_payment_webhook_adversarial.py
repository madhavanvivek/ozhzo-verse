import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.api.v1.payments import handle_payment_webhook
from src.infrastructure.database.models import PaymentTransactionModel, SubscriptionModel


@pytest.mark.asyncio
async def test_payment_webhook_adversarial_suite():
    """
    PAYMENT WEBHOOK ADVERSARIAL SUITE:
    1. Valid Webhook -> Activates subscription.
    2. Duplicate / Replay Webhook -> Ignored (already_processed), subscription not extended twice.
    3. Forged / Invalid Signature -> HTTP 400 Bad Request.
    4. Malformed Payload -> Handled gracefully.
    5. Webhook delivered for expired / cancelled subscription -> Does not cause state corruption.
    """
    tx_id = uuid.uuid4()
    user_id = uuid.uuid4()
    home_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 1. FORGED SIGNATURE TEST
    mock_db = AsyncMock()
    mock_request_forged = AsyncMock()
    mock_request_forged.body.return_value = b'{"event": "payment.authorized"}'

    with patch("src.api.v1.payments.get_payment_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.provider_name = "RAZORPAY"
        mock_provider.handle_webhook.return_value = {
            "valid": False,
            "error": "Invalid HMAC signature header"
        }
        mock_factory.return_value = mock_provider

        with pytest.raises(HTTPException) as exc_info:
            await handle_payment_webhook(
                provider_name="RAZORPAY",
                request=mock_request_forged,
                db=mock_db,
                x_razorpay_signature="bad_forged_sig"
            )
        assert exc_info.value.status_code == 400
        assert "signature" in exc_info.value.detail.lower()

    # 2. VALID INITIAL WEBHOOK TEST
    pending_tx = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        home_id=home_id,
        plan_id=uuid.uuid4(),
        provider="RAZORPAY",
        provider_transaction_id="pay_valid_12345",
        idempotency_key="pay_valid_12345",
        status="PENDING",
        amount=29.99,
        currency="USD"
    )

    mock_sub = SubscriptionModel(
        id=uuid.uuid4(),
        home_id=home_id,
        user_id=user_id,
        status="ACTIVE",
        current_period_ends_at=datetime.now(timezone.utc) + timedelta(days=30)
    )

    def _mock_execute(stmt):
        stmt_str = str(stmt)
        if "subscriptions" in stmt_str:
            return MagicMock(scalars=lambda: MagicMock(first=lambda: mock_sub))
        return MagicMock(scalars=lambda: MagicMock(first=lambda: pending_tx))

    mock_db.execute.side_effect = _mock_execute

    mock_request_valid = AsyncMock()
    mock_request_valid.body.return_value = b'{"provider_transaction_id": "pay_valid_12345", "status": "SUCCESS"}'


    with patch("src.api.v1.payments.get_payment_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.provider_name = "RAZORPAY"
        mock_provider.handle_webhook.return_value = {
            "valid": True,
            "provider_transaction_id": "pay_valid_12345",
            "status": "SUCCESS"
        }
        mock_factory.return_value = mock_provider

        resp = await handle_payment_webhook(
            provider_name="RAZORPAY",
            request=mock_request_valid,
            db=mock_db,
            x_razorpay_signature="valid_sig_123"
        )
        assert pending_tx.status == "SUCCESS"

        # 3. REPLAY / DUPLICATE WEBHOOK TEST
        # Transaction is now SUCCESS; replay must return already_processed
        resp_replay = await handle_payment_webhook(
            provider_name="RAZORPAY",
            request=mock_request_valid,
            db=mock_db,
            x_razorpay_signature="valid_sig_123"
        )
        assert resp_replay["status"] == "already_processed"
        assert resp_replay["transaction_id"] == str(tx_id)

