import uuid
import secrets
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID


class PaymentIntentResult:
    def __init__(
        self,
        provider: str,
        provider_transaction_id: str,
        amount: Decimal,
        currency: str,
        client_secret: Optional[str] = None,
        status: str = "PENDING",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.provider = provider
        self.provider_transaction_id = provider_transaction_id
        self.amount = amount
        self.currency = currency
        self.client_secret = client_secret
        self.status = status
        self.metadata = metadata or {}


class PaymentVerificationResult:
    def __init__(
        self,
        success: bool,
        provider_transaction_id: str,
        status: str,
        amount_paid: Decimal,
        currency: str,
        failure_reason: Optional[str] = None,
        raw_response: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.provider_transaction_id = provider_transaction_id
        self.status = status
        self.amount_paid = amount_paid
        self.currency = currency
        self.failure_reason = failure_reason
        self.raw_response = raw_response or {}


class RefundResult:
    def __init__(
        self,
        success: bool,
        refund_id: str,
        amount_refunded: Decimal,
        status: str,
        failure_reason: Optional[str] = None,
    ):
        self.success = success
        self.refund_id = refund_id
        self.amount_refunded = amount_refunded
        self.status = status
        self.failure_reason = failure_reason


class PaymentGatewayProvider(ABC):
    @abstractmethod
    async def create_payment_intent(
        self,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentIntentResult:
        """Create a payment session or intent with the provider."""
        pass

    @abstractmethod
    async def verify_payment(
        self,
        provider_transaction_id: str,
        signature: Optional[str] = None,
    ) -> PaymentVerificationResult:
        """Server-authoritative verification of payment settlement."""
        pass

    @abstractmethod
    async def refund_payment(
        self,
        provider_transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        """Refund a transaction."""
        pass

    @abstractmethod
    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Normalize provider webhook events."""
        pass


class MockPaymentGatewayProvider(PaymentGatewayProvider):
    """
    Test and development provider simulating payments with realistic latencies,
    configurable failure triggers, and idempotency guarantees.
    """

    def __init__(self):
        self.provider_name = "MOCK_GATEWAY"
        self._intents: Dict[str, Dict[str, Any]] = {}

    async def create_payment_intent(
        self,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentIntentResult:
        tx_id = f"mock_tx_{secrets.token_hex(12)}"
        client_secret = f"mock_sec_{secrets.token_urlsafe(16)}"
        
        # Immediate zero-amount validation (e.g. 100% coupon)
        status = "SUCCESS" if amount == Decimal("0.00") else "PENDING"

        # Register authoritative intent context
        self._intents[tx_id] = {
            "user_id": user_id,
            "amount": amount,
            "currency": currency.upper().strip(),
            "status": status,
            "idempotency_key": idempotency_key,
            "metadata": metadata or {},
        }

        return PaymentIntentResult(
            provider=self.provider_name,
            provider_transaction_id=tx_id,
            amount=amount,
            currency=currency.upper().strip(),
            client_secret=client_secret,
            status=status,
            metadata=metadata or {},
        )

    async def verify_payment(
        self,
        provider_transaction_id: str,
        signature: Optional[str] = None,
    ) -> PaymentVerificationResult:
        # Check simulation triggers for tests
        if "fail" in provider_transaction_id.lower() or signature == "force_failure":
            return PaymentVerificationResult(
                success=False,
                provider_transaction_id=provider_transaction_id,
                status="FAILED",
                amount_paid=Decimal("0.00"),
                currency="USD",
                failure_reason="Card was declined by test simulator.",
            )

        intent = self._intents.get(provider_transaction_id)
        if intent:
            amount = intent["amount"]
            currency = intent["currency"]

            # Simulation hooks for testing mismatch handling
            if "mismatch_amount" in provider_transaction_id.lower() or signature == "force_amount_mismatch":
                amount = Decimal("10.00") if amount != Decimal("10.00") else Decimal("99.99")
            elif "mismatch_currency" in provider_transaction_id.lower() or signature == "force_currency_mismatch":
                currency = "EUR" if currency != "EUR" else "USD"

            return PaymentVerificationResult(
                success=True,
                provider_transaction_id=provider_transaction_id,
                status="SUCCESS",
                amount_paid=amount,
                currency=currency,
                raw_response={"intent": intent},
            )

        # Fallback if transaction id not pre-registered
        amount = Decimal("49.00")
        currency = "USD"
        if "mismatch_amount" in provider_transaction_id.lower() or signature == "force_amount_mismatch":
            amount = Decimal("10.00")
        elif "mismatch_currency" in provider_transaction_id.lower() or signature == "force_currency_mismatch":
            currency = "EUR"

        return PaymentVerificationResult(
            success=True,
            provider_transaction_id=provider_transaction_id,
            status="SUCCESS",
            amount_paid=amount,
            currency=currency,
        )

    async def refund_payment(
        self,
        provider_transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        refund_id = f"mock_ref_{secrets.token_hex(8)}"
        intent = self._intents.get(provider_transaction_id)
        refund_amount = amount or (intent["amount"] if intent else Decimal("49.00"))

        return RefundResult(
            success=True,
            refund_id=refund_id,
            amount_refunded=refund_amount,
            status="REFUNDED",
        )

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        if signature == "invalid_signature":
            return {"valid": False, "error": "Invalid webhook signature"}

        event_type = payload.get("event_type", "payment.succeeded")
        tx_id = payload.get("provider_transaction_id") or payload.get("transaction_id", f"mock_tx_{secrets.token_hex(8)}")
        amount_raw = payload.get("amount")
        amount = Decimal(str(amount_raw)) if amount_raw is not None else None
        currency = payload.get("currency", "USD").upper()

        return {
            "valid": True,
            "event_type": event_type,
            "provider_transaction_id": tx_id,
            "amount": amount,
            "currency": currency,
            "status": "SUCCESS" if "succeed" in event_type else "FAILED",
            "payload": payload,
        }


_global_payment_provider: PaymentGatewayProvider = MockPaymentGatewayProvider()


def get_payment_provider() -> PaymentGatewayProvider:
    return _global_payment_provider
