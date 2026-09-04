import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.schemas.common import ApiSuccessResponse
from src.domain.entitlements import (
    compute_subscription_lifecycle_status,
    provision_paid_home_entitlement,
    record_audit_log,
)
from src.domain.payments import (
    get_gateway_status_summary,
    get_payment_provider,
)
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    HomeAccessEntitlementModel,
    HomeModel,
    NotificationModel,
    PaymentTransactionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
)

logger = logging.getLogger("ozhzo.payments")

router = APIRouter()


# ==============================================================================
# 1. PUBLIC GATEWAY INFO (FOR FRONTEND CHECKOUT INITIALIZATION)
# ==============================================================================

@router.get("/gateway-info", response_model=ApiSuccessResponse[Dict[str, Any]])
async def get_client_gateway_info():
    """
    Returns public, client-safe payment gateway configuration (e.g. publishable key,
    active provider, environment, supported currencies). NEVER leaks secret keys.
    """
    provider = get_payment_provider()
    provider_name = provider.provider_name

    key_id = None
    if provider_name == "RAZORPAY":
        key_id = settings.RAZORPAY_KEY_ID or "rzp_test_placeholder"
    elif provider_name == "STRIPE":
        key_id = settings.STRIPE_PUBLISHABLE_KEY or "pk_test_placeholder"
    else:
        key_id = "mock_client_key"

    return ApiSuccessResponse(
        data={
            "provider": provider_name,
            "environment": settings.PAYMENT_GATEWAY_ENVIRONMENT,
            "publishable_key": key_id,
            "supported_currencies": ["USD", "INR", "EUR", "GBP", "AUD", "CAD", "SGD", "AED"],
        },
        message="Gateway info retrieved."
    )


# ==============================================================================
# 2. AUTHORITATIVE PAYMENT WEBHOOK (RAZORPAY / STRIPE / MOCK)
# ==============================================================================

@router.post("/webhook/{provider_name}")
async def handle_payment_webhook(
    provider_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: Optional[str] = Header(None, alias="x-razorpay-signature"),
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    x_signature: Optional[str] = Header(None, alias="x-signature"),
):
    """
    Authoritative server-side webhook endpoint for payment gateways.
    1. Validates webhook signature against server secrets.
    2. Enforces idempotency to prevent duplicate settlement.
    3. Activates/renews subscription and provisions access entitlements on SUCCESS.
    4. Records failure status and emits PRIORITY notifications on FAILED.
    """
    raw_body = await request.body()
    try:
        payload_data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        payload_data = {}

    sig = x_razorpay_signature or stripe_signature or x_signature or ""

    provider = get_payment_provider(provider_name)
    webhook_result = await provider.handle_webhook(payload_data or raw_body, signature=sig)

    if not webhook_result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=webhook_result.get("error", "Invalid webhook signature or payload.")
        )

    provider_tx_id = webhook_result.get("provider_transaction_id")
    event_status = webhook_result.get("status", "SUCCESS")
    event_type = webhook_result.get("event_type", "payment.event")

    # Locate authoritative PaymentTransaction record
    transaction: Optional[PaymentTransactionModel] = None
    if provider_tx_id:
        tx_q = select(PaymentTransactionModel).where(
            (PaymentTransactionModel.provider_transaction_id == provider_tx_id) |
            (PaymentTransactionModel.idempotency_key == provider_tx_id)
        )
        transaction = (await db.execute(tx_q)).scalars().first()

    # Fallback to metadata transaction_id if provided
    if not transaction and isinstance(payload_data, dict):
        meta_tx_id = payload_data.get("metadata", {}).get("transaction_id") or payload_data.get("transaction_id")
        if meta_tx_id:
            try:
                transaction = await db.get(PaymentTransactionModel, UUID(str(meta_tx_id)))
            except Exception:
                transaction = None

    if not transaction:
        logger.info(f"Webhook received for unknown transaction or non-application order: {provider_tx_id}")
        return {"status": "ignored", "reason": "No matching application transaction found."}

    # IDEMPOTENCY GUARD: If already processed successfully, avoid duplicate subscription extension
    if transaction.status == "SUCCESS":
        return {
            "status": "already_processed",
            "transaction_id": str(transaction.id),
            "message": "Payment has already been processed successfully."
        }

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------------------------
    # CASE A: PAYMENT SUCCEEDED
    # --------------------------------------------------------------------------
    if event_status == "SUCCESS":
        transaction.status = "SUCCESS"
        transaction.updated_at = now
        if provider_tx_id:
            transaction.provider_transaction_id = provider_tx_id

        # Update or create subscription with Rule 10 renewal duration
        sub = None
        if transaction.home_id:
            sub_q = select(SubscriptionModel).where(SubscriptionModel.home_id == transaction.home_id)
            sub = (await db.execute(sub_q)).scalars().first()

        if not sub:
            sub_user_q = select(SubscriptionModel).where(SubscriptionModel.user_id == transaction.user_id)
            sub = (await db.execute(sub_user_q)).scalars().first()

        if sub:
            sub.plan_id = transaction.plan_id
            sub.price_id = transaction.price_id
            sub.status = "ACTIVE"
            sub.user_id = transaction.user_id
            sub.updated_at = now

            # RULE 10: If active/expiring (current_period_ends_at > now), extend from current expiry
            sub_end = sub.current_period_ends_at if (sub.current_period_ends_at and sub.current_period_ends_at.tzinfo) else (sub.current_period_ends_at.replace(tzinfo=timezone.utc) if sub.current_period_ends_at else None)
            if sub_end and sub_end > now:
                ends_at = sub_end + timedelta(days=365)
            else:
                sub.current_period_starts_at = now
                ends_at = now + timedelta(days=365)
            sub.current_period_ends_at = ends_at
        else:
            ends_at = now + timedelta(days=365)
            target_home_id = transaction.home_id
            if not target_home_id:
                h_q = select(HomeModel.id).where(HomeModel.created_by == transaction.user_id).limit(1)
                target_home_id = (await db.execute(h_q)).scalar_one_or_none()

            if not target_home_id:
                target_home_id = uuid.uuid4()
                placeholder_home = HomeModel(
                    id=target_home_id,
                    name="Primary Household",
                    created_by=transaction.user_id,
                    status="ACTIVE",
                    deleted_at=datetime.now(timezone.utc)
                )
                db.add(placeholder_home)
                await db.flush()

            sub = SubscriptionModel(
                id=uuid.uuid4(),
                home_id=target_home_id,
                user_id=transaction.user_id,
                plan_id=transaction.plan_id,
                price_id=transaction.price_id,
                active_coupon_id=transaction.coupon_id,
                status="ACTIVE",
                introductory_period_starts_at=now,
                introductory_period_ends_at=ends_at,
                current_period_starts_at=now,
                current_period_ends_at=ends_at,
                paid_member_seats=0,
                currency_snapshot=transaction.currency,
                effective_price_snapshot=transaction.final_amount,
                list_price_snapshot=transaction.amount,
                discount_amount_snapshot=transaction.discount_amount,
                created_at=now,
                updated_at=now
            )
            db.add(sub)
            await db.flush()

        transaction.subscription_id = sub.id

        # Sync or provision HomeAccessEntitlementModel
        target_user = await db.get(UserModel, transaction.user_id)
        if target_user and sub.home_id:
            home = await db.get(HomeModel, sub.home_id)
            if home:
                await provision_paid_home_entitlement(
                    user=target_user,
                    home=home,
                    subscription_id=sub.id,
                    db=db,
                    expires_at=sub.current_period_ends_at
                )

        # Audit log
        await record_audit_log(
            db=db,
            entity_type="PAYMENT",
            entity_id=transaction.id,
            action="WEBHOOK_PAYMENT_SUCCESS",
            performed_by=transaction.user_id,
            new_values={
                "status": "SUCCESS",
                "provider": provider_name,
                "provider_transaction_id": provider_tx_id,
                "amount": str(transaction.final_amount),
                "currency": transaction.currency,
            },
            reason=f"Authoritative webhook confirmation ({event_type})."
        )

        # Idempotently emit payment confirmation notification
        dedup = f"pay_success_{transaction.id}"
        existing_n = (await db.execute(select(NotificationModel.id).where(NotificationModel.dedup_key == dedup))).scalars().first()
        if not existing_n:
            notif = NotificationModel(
                id=uuid.uuid4(),
                home_id=transaction.home_id,
                user_id=transaction.user_id,
                title="Payment Confirmed",
                body=f"Your subscription payment of {transaction.currency} {transaction.final_amount} was successfully processed.",
                type="PAYMENT_CONFIRMED",
                priority="NORMAL",
                action_type="VIEW",
                action_url="/settings/subscription",
                action_label="View Subscription",
                dedup_key=dedup,
                is_read=False,
                created_at=now
            )
            db.add(notif)

    # --------------------------------------------------------------------------
    # CASE B: PAYMENT FAILED
    # --------------------------------------------------------------------------
    else:
        transaction.status = "FAILED"
        transaction.failure_reason = webhook_result.get("failure_reason") or f"Payment failed via {provider_name} webhook ({event_type})."
        transaction.updated_at = now

        # Emit high-urgency PRIORITY notification with Retry CTA
        dedup = f"pay_failed_{transaction.id}"
        existing_n = (await db.execute(select(NotificationModel.id).where(NotificationModel.dedup_key == dedup))).scalars().first()
        if not existing_n:
            notif = NotificationModel(
                id=uuid.uuid4(),
                home_id=transaction.home_id,
                user_id=transaction.user_id,
                title="Payment Failed",
                body=f"Your subscription payment of {transaction.currency} {transaction.final_amount} could not be processed. Please retry to maintain uninterrupted access.",
                type="PAYMENT_FAILED",
                priority="PRIORITY",
                requires_action=True,
                action_status="OPEN",
                action_type="RETRY_PAYMENT",
                action_url="/settings/subscription",
                action_label="Retry Payment",
                dedup_key=dedup,
                is_read=False,
                created_at=now
            )
            db.add(notif)

        await record_audit_log(
            db=db,
            entity_type="PAYMENT",
            entity_id=transaction.id,
            action="WEBHOOK_PAYMENT_FAILED",
            performed_by=transaction.user_id,
            new_values={
                "status": "FAILED",
                "failure_reason": transaction.failure_reason,
            },
            reason=f"Payment failure received from webhook ({event_type})."
        )

    await db.commit()

    return {
        "status": "processed",
        "transaction_id": str(transaction.id),
        "payment_status": transaction.status,
        "subscription_id": str(transaction.subscription_id) if transaction.subscription_id else None,
    }
