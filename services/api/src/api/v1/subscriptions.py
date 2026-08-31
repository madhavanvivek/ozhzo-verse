import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    CampaignModel,
    CouponModel,
    CouponRedemptionModel,
    HomeMemberModel,
    HomeModel,
    PaymentTransactionModel,
    PromotionModel,
    PromotionRedemptionModel,
    SubscriptionFeatureModel,
    SubscriptionGrantModel,
    SubscriptionModel,
    SubscriptionPlanFeatureModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel,
    UserProfileModel
)
from src.domain.entitlements import get_user_entitlement_summary
from src.domain.payments import get_payment_provider
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse
from src.schemas.coupon import ApplyCouponRequest, ApplyCouponResponse, CouponDTO
from src.schemas.subscription import (
    CalculateSubscriptionRequest,
    CalculateSubscriptionResponse,
    CheckoutSubscriptionRequest,
    CheckoutSubscriptionResponse,
    ConfirmPaymentRequest,
    ConfirmPaymentResponse,
    HomeSubscriptionOverviewDTO,
    MemberEntitlementDTO,
    PaymentTransactionDTO,
    PromotionDTO,
    SubscriptionFeatureDTO,
    SubscriptionPlanDetailDTO,
    SubscriptionPriceDTO,
    UpdateSubscriptionSeatsRequest,
    UserEntitlementSummaryDTO
)

router = APIRouter(prefix="/subscription", tags=["Subscriptions"])


# ------------------------------------------------------------------------------
# Default Data Bootstrapper
# ------------------------------------------------------------------------------

async def bootstrap_default_subscription_data(db: AsyncSession) -> SubscriptionPlanModel:
    query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.code == "OZHZO_HOME")
    res = await db.execute(query)
    plan = res.scalar_one_or_none()

    if not plan:
        plan = SubscriptionPlanModel(
            name="Ozhzo Home Standard",
            code="OZHZO_HOME",
            description="The complete digital operating system for households.",
            plan_type="HOME",
            status="ACTIVE",
            included_members=1,
            maximum_members=10,
            additional_member_allowed=True,
            introductory_enabled=True,
            introductory_duration_days=365,
            introductory_price=Decimal("0.00")
        )
        db.add(plan)
        await db.flush()

        # Regional Standard / List Prices (Development Seed Values)
        price_us = SubscriptionPriceModel(
            plan_id=plan.id, country="US", region="NORTH_AMERICA", currency="USD", billing_period="ANNUAL",
            list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"),
            base_price=Decimal("0.00"), additional_member_price=Decimal("10.00"), version=1, is_active=True
        )
        price_global = SubscriptionPriceModel(
            plan_id=plan.id, country="GLOBAL", region="GLOBAL", currency="USD", billing_period="ANNUAL",
            list_price=Decimal("0.00"), additional_member_list_price=Decimal("20.00"),
            base_price=Decimal("0.00"), additional_member_price=Decimal("10.00"), version=1, is_active=True
        )
        price_in = SubscriptionPriceModel(
            plan_id=plan.id, country="IN", region="SOUTH_ASIA", currency="INR", billing_period="ANNUAL",
            list_price=Decimal("0.00"), additional_member_list_price=Decimal("1799.00"),
            base_price=Decimal("0.00"), additional_member_price=Decimal("899.50"), version=1, is_active=True
        )
        price_ae = SubscriptionPriceModel(
            plan_id=plan.id, country="AE", region="MIDDLE_EAST", currency="AED", billing_period="ANNUAL",
            list_price=Decimal("0.00"), additional_member_list_price=Decimal("99.00"),
            base_price=Decimal("0.00"), additional_member_price=Decimal("49.50"), version=1, is_active=True
        )
        price_gb = SubscriptionPriceModel(
            plan_id=plan.id, country="GB", region="EUROPE", currency="GBP", billing_period="ANNUAL",
            list_price=Decimal("0.00"), additional_member_list_price=Decimal("16.00"),
            base_price=Decimal("0.00"), additional_member_price=Decimal("8.00"), version=1, is_active=True
        )
        db.add_all([price_us, price_global, price_in, price_ae, price_gb])

        # Default Launch Campaign & Promotion
        launch_promo = PromotionModel(
            name="Launch 50% Off Early Adopter Promotion",
            code="LAUNCH50",
            description="50% lifetime discount on additional family member seats.",
            discount_type="PERCENTAGE",
            discount_value=Decimal("50.00"),
            status="ACTIVE",
            applicable_plan_id=plan.id,
            new_users_only=False,
            existing_users_allowed=True,
            maximum_redemptions=100000,
            maximum_redemptions_per_user=1
        )
        db.add(launch_promo)

        # Core Features
        features_data = [
            ("INVENTORY", "Household Inventory", "Stock tracking & low-stock alerts"),
            ("SHOPPING", "Shared Shopping Lists", "Optimistic live in-store grocery synchronization"),
            ("TASKS", "Household Tasks & Chores", "Chore assignments and recurrence rules"),
            ("BILLS", "Bills & Reminders", "Recurring bills, payment logging & reminders"),
            ("CALENDAR", "Family Calendar", "Schedules, appointments & RSVP tracking")
        ]
        for f_code, f_name, f_desc in features_data:
            feat_query = select(SubscriptionFeatureModel).where(SubscriptionFeatureModel.code == f_code)
            feat = (await db.execute(feat_query)).scalar_one_or_none()
            if not feat:
                feat = SubscriptionFeatureModel(code=f_code, name=f_name, description=f_desc, is_active=True)
                db.add(feat)
                await db.flush()

            db.add(SubscriptionPlanFeatureModel(plan_id=plan.id, feature_id=feat.id, is_enabled=True))

        await db.commit()

    return plan


get_or_create_default_plan = bootstrap_default_subscription_data


async def get_or_init_home_subscription(home_id: UUID, db: AsyncSession) -> SubscriptionModel:
    query = (
        select(SubscriptionModel)
        .options(selectinload(SubscriptionModel.plan), selectinload(SubscriptionModel.price))
        .where(SubscriptionModel.home_id == home_id)
    )
    res = await db.execute(query)
    sub = res.scalar_one_or_none()

    if not sub:
        plan = await bootstrap_default_subscription_data(db)
        price_query = select(SubscriptionPriceModel).where(
            SubscriptionPriceModel.plan_id == plan.id,
            SubscriptionPriceModel.country == "GLOBAL",
            SubscriptionPriceModel.is_active == True
        )
        price = (await db.execute(price_query)).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        intro_ends = now + timedelta(days=plan.introductory_duration_days)

        sub = SubscriptionModel(
            home_id=home_id,
            plan_id=plan.id,
            price_id=price.id if price else None,
            status="TRIALING",
            introductory_period_starts_at=now,
            introductory_period_ends_at=intro_ends,
            current_period_starts_at=now,
            current_period_ends_at=intro_ends,
            paid_member_seats=0,
            
            # Historical Snapshot
            list_price_snapshot=price.list_price if price else Decimal("0.00"),
            additional_member_list_price_snapshot=price.additional_member_list_price if price else Decimal("20.00"),
            discount_type_snapshot="PERCENTAGE",
            discount_value_snapshot=Decimal("50.00"),
            discount_amount_snapshot=Decimal("10.00"),
            effective_price_snapshot=Decimal("10.00"),
            promotion_code_snapshot="LAUNCH50",
            currency_snapshot=price.currency if price else "USD",
            pricing_date_snapshot=now,
            renewal_policy="KEEP_ORIGINAL_PRICE",
            
            currency=price.currency if price else "USD",
            base_price_locked=Decimal("0.00"),
            additional_member_price_locked=Decimal("10.00")
        )
        db.add(sub)
        await db.commit()

    return sub


# ------------------------------------------------------------------------------
# Authoritative Coupon & Promotion Evaluator
# ------------------------------------------------------------------------------

def compute_free_days(value: int, unit: str) -> int:
    unit_upper = unit.upper()
    if unit_upper == "DAYS":
        return value
    elif unit_upper == "MONTHS":
        return value * 30
    elif unit_upper == "YEARS":
        return value * 365
    return value * 30


async def evaluate_coupon(
    coupon_code: Optional[str],
    plan_id: UUID,
    country: Optional[str],
    state: Optional[str],
    district: Optional[str],
    postal_code: Optional[str],
    currency: str,
    user_id: Optional[UUID],
    home_id: Optional[UUID],
    db: AsyncSession
) -> Tuple[Optional[CouponModel], bool, str]:
    if not coupon_code:
        return None, False, "No coupon code provided."

    query = select(CouponModel).where(CouponModel.code == coupon_code.upper().strip())
    coupon = (await db.execute(query)).scalar_one_or_none()

    if not coupon:
        return None, False, f"Coupon code '{coupon_code}' is invalid."

    now = datetime.now(timezone.utc)

    # 1. Status check
    if coupon.status != "ACTIVE":
        return None, False, f"Coupon '{coupon.code}' is inactive."

    # 2. Date range check
    if coupon.start_date and now < coupon.start_date:
        return None, False, f"Coupon '{coupon.code}' has not started yet."
    if coupon.end_date and now > coupon.end_date:
        return None, False, f"Coupon '{coupon.code}' has expired."

    # 3. Maximum total redemptions
    if coupon.maximum_total_redemptions is not None and coupon.redemptions_count >= coupon.maximum_total_redemptions:
        return None, False, f"Coupon '{coupon.code}' has reached its maximum total redemption limit."

    # 4. User-Specific / Home-Specific Binding
    if coupon.target_user_id and user_id and coupon.target_user_id != user_id:
        return None, False, f"Coupon '{coupon.code}' is exclusively reserved for a specific user."
    if coupon.target_home_id and home_id and coupon.target_home_id != home_id:
        return None, False, f"Coupon '{coupon.code}' is exclusively reserved for a specific Home."

    # 5. Per-User Redemption Limit
    if user_id:
        user_redemptions_query = select(func.count(CouponRedemptionModel.id)).where(
            CouponRedemptionModel.coupon_id == coupon.id,
            CouponRedemptionModel.user_id == user_id
        )
        user_redemptions = (await db.execute(user_redemptions_query)).scalar() or 0
        if coupon.maximum_redemptions_per_user is not None and user_redemptions >= coupon.maximum_redemptions_per_user:
            return None, False, f"You have already redeemed coupon '{coupon.code}' the maximum allowed number of times."

    # 6. Per-Home Redemption Limit
    if home_id:
        home_redemptions_query = select(func.count(CouponRedemptionModel.id)).where(
            CouponRedemptionModel.coupon_id == coupon.id,
            CouponRedemptionModel.home_id == home_id
        )
        home_redemptions = (await db.execute(home_redemptions_query)).scalar() or 0
        if coupon.maximum_redemptions_per_home is not None and home_redemptions >= coupon.maximum_redemptions_per_home:
            return None, False, f"Coupon '{coupon.code}' has already been redeemed for this Home."

    # 7. Geographic Restrictions (Country, State, District, Postal Code)
    if coupon.country and country and coupon.country.upper() not in [country.upper(), "GLOBAL"]:
        return None, False, f"Coupon '{coupon.code}' is not valid in country {country}."
    if coupon.state and state and coupon.state.lower() != state.lower():
        return None, False, f"Coupon '{coupon.code}' is restricted to state/province {coupon.state}."
    if coupon.district and district and coupon.district.lower() != district.lower():
        return None, False, f"Coupon '{coupon.code}' is restricted to district {coupon.district}."
    if coupon.postal_code and postal_code and coupon.postal_code.strip() != postal_code.strip():
        return None, False, f"Coupon '{coupon.code}' is restricted to postal code {coupon.postal_code}."

    # 8. Currency Restrictions
    if coupon.currency and coupon.currency.upper() != currency.upper():
        return None, False, f"Coupon '{coupon.code}' is valid only for {coupon.currency}."

    # 9. Plan Compatibility
    if coupon.applicable_plan_id and coupon.applicable_plan_id != plan_id:
        return None, False, f"Coupon '{coupon.code}' is not applicable to this subscription plan."

    # 10. Eligibility Type (e.g., NEW_USER)
    if coupon.eligibility_type == "NEW_USER" and user_id:
        prev_sub = (await db.execute(select(SubscriptionModel).where(
            SubscriptionModel.home_id.in_(select(HomeModel.id).where(HomeModel.created_by == user_id))
        ))).first()
        if prev_sub:
            return None, False, f"Coupon '{coupon.code}' is reserved for new users only."

    return coupon, True, "Coupon applied successfully."


async def evaluate_promotion(
    promotion_code: Optional[str],
    plan_id: UUID,
    country: str,
    currency: str,
    user_id: Optional[UUID],
    db: AsyncSession
) -> Tuple[Optional[PromotionModel], bool, str]:
    if not promotion_code:
        return None, False, "No promotion code provided."

    query = select(PromotionModel).where(PromotionModel.code == promotion_code.upper().strip())
    promo = (await db.execute(query)).scalar_one_or_none()

    if not promo:
        return None, False, f"Promotion code '{promotion_code}' is invalid."

    now = datetime.now(timezone.utc)

    if promo.status != "ACTIVE":
        return None, False, f"Promotion code '{promo.code}' is inactive."
    if promo.start_date and now < promo.start_date:
        return None, False, f"Promotion code '{promo.code}' has not started yet."
    if promo.end_date and now > promo.end_date:
        return None, False, f"Promotion code '{promo.code}' has expired."
    if promo.country and promo.country != "GLOBAL" and promo.country != country:
        return None, False, f"Promotion code '{promo.code}' is not valid in region {country}."
    if promo.currency and promo.currency != currency:
        return None, False, f"Promotion code '{promo.code}' is not valid for currency {currency}."
    if promo.applicable_plan_id and promo.applicable_plan_id != plan_id:
        return None, False, f"Promotion code '{promo.code}' is not applicable to this plan."
    if promo.maximum_redemptions is not None and promo.redemptions_count >= promo.maximum_redemptions:
        return None, False, f"Promotion code '{promo.code}' has reached its maximum redemption limit."
    if promo.new_users_only and user_id:
        prev_sub = (await db.execute(select(SubscriptionModel).where(
            SubscriptionModel.home_id.in_(select(HomeModel.id).where(HomeModel.created_by == user_id))
        ))).first()
        if prev_sub:
            return None, False, f"Promotion code '{promo.code}' is reserved for new users only."

    return promo, True, "Promotion code applied successfully."


# ------------------------------------------------------------------------------
# Public & Client APIs
# ------------------------------------------------------------------------------

@router.get("/plans", response_model=ApiSuccessResponse[List[SubscriptionPlanDetailDTO]])
async def list_subscription_plans(
    country: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    await bootstrap_default_subscription_data(db)

    query = (
        select(SubscriptionPlanModel)
        .options(
            selectinload(SubscriptionPlanModel.prices),
            selectinload(SubscriptionPlanModel.plan_features).selectinload(SubscriptionPlanFeatureModel.feature)
        )
        .where(SubscriptionPlanModel.status == "ACTIVE")
    )
    plans = (await db.execute(query)).scalars().all()

    dtos = []
    for p in plans:
        filtered_prices = p.prices
        if country:
            filtered_prices = [pr for pr in filtered_prices if pr.country in [country.upper(), "GLOBAL"]]
        if currency:
            filtered_prices = [pr for pr in filtered_prices if pr.currency == currency.upper()]

        price_dtos = [
            SubscriptionPriceDTO(
                id=pr.id,
                plan_id=pr.plan_id,
                country=pr.country,
                region=pr.region,
                currency=pr.currency,
                billing_period=pr.billing_period,
                list_price=pr.list_price,
                additional_member_list_price=pr.additional_member_list_price,
                base_price=pr.base_price,
                additional_member_price=pr.additional_member_price,
                version=pr.version,
                is_active=pr.is_active,
                effective_from=pr.effective_from,
                effective_until=pr.effective_until
            )
            for pr in filtered_prices if pr.is_active
        ]

        feature_dtos = [
            SubscriptionFeatureDTO(
                id=pf.feature.id,
                code=pf.feature.code,
                name=pf.feature.name,
                description=pf.feature.description,
                is_enabled=pf.is_enabled,
                entitlement_limit=pf.entitlement_limit
            )
            for pf in p.plan_features if pf.feature and pf.feature.is_active
        ]

        dtos.append(
            SubscriptionPlanDetailDTO(
                id=p.id,
                name=p.name,
                code=p.code,
                description=p.description,
                plan_type=p.plan_type,
                status=p.status,
                included_members=p.included_members,
                maximum_members=p.maximum_members,
                additional_member_allowed=p.additional_member_allowed,
                introductory_enabled=p.introductory_enabled,
                introductory_duration_days=p.introductory_duration_days,
                introductory_price=p.introductory_price,
                prices=price_dtos,
                features=feature_dtos
            )
        )

    return ApiSuccessResponse(data=dtos)


@router.get("/pricing/current", response_model=ApiSuccessResponse[SubscriptionPriceDTO])
async def get_current_pricing(
    country: str = Query(default="GLOBAL"),
    currency: Optional[str] = Query(None),
    billing_period: str = Query(default="ANNUAL"),
    plan_code: str = Query(default="OZHZO_HOME"),
    db: AsyncSession = Depends(get_db),
):
    await bootstrap_default_subscription_data(db)

    query = (
        select(SubscriptionPriceModel)
        .join(SubscriptionPlanModel, SubscriptionPriceModel.plan_id == SubscriptionPlanModel.id)
        .where(
            SubscriptionPlanModel.code == plan_code,
            SubscriptionPriceModel.country == country.upper(),
            SubscriptionPriceModel.billing_period == billing_period.upper(),
            SubscriptionPriceModel.is_active == True
        )
        .order_by(SubscriptionPriceModel.version.desc())
    )
    price = (await db.execute(query)).scalar_one_or_none()

    if not price:
        query_global = (
            select(SubscriptionPriceModel)
            .join(SubscriptionPlanModel, SubscriptionPriceModel.plan_id == SubscriptionPlanModel.id)
            .where(
                SubscriptionPlanModel.code == plan_code,
                SubscriptionPriceModel.country == "GLOBAL",
                SubscriptionPriceModel.billing_period == billing_period.upper(),
                SubscriptionPriceModel.is_active == True
            )
            .order_by(SubscriptionPriceModel.version.desc())
        )
        price = (await db.execute(query_global)).scalar_one_or_none()

    if not price:
        raise HTTPException(status_code=404, detail="Active pricing configuration not found.")

    return ApiSuccessResponse(
        data=SubscriptionPriceDTO(
            id=price.id,
            plan_id=price.plan_id,
            country=price.country,
            region=price.region,
            currency=price.currency,
            billing_period=price.billing_period,
            list_price=price.list_price,
            additional_member_list_price=price.additional_member_list_price,
            base_price=price.base_price,
            additional_member_price=price.additional_member_price,
            version=price.version,
            is_active=price.is_active,
            effective_from=price.effective_from,
            effective_until=price.effective_until
        )
    )


@router.post("/calculate", response_model=ApiSuccessResponse[CalculateSubscriptionResponse])
async def calculate_subscription_price(
    payload: CalculateSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritative Centralized Pricing Calculator.
    Evaluates Standard List Price + Coupons (Free Periods, Percentage, Fixed) + Promotions.
    """
    # 1. Lookup Plan
    plan_query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.code == (payload.plan_code or "OZHZO_HOME"))
    plan = (await db.execute(plan_query)).scalar_one_or_none()
    if not plan:
        try:
            await bootstrap_default_subscription_data(db)
            plan = (await db.execute(plan_query)).scalar_one_or_none()
        except Exception:
            pass

    if not plan or getattr(plan, "status", "ACTIVE") != "ACTIVE":
        raise HTTPException(status_code=404, detail="Active subscription plan not found.")

    # 2. Lookup Regional Standard List Price
    country_code = (payload.country or "GLOBAL").upper()
    period = (payload.billing_period or "ANNUAL").upper()

    price_query = (
        select(SubscriptionPriceModel)
        .where(
            SubscriptionPriceModel.plan_id == plan.id,
            SubscriptionPriceModel.country == country_code,
            SubscriptionPriceModel.billing_period == period,
            SubscriptionPriceModel.is_active == True
        )
        .order_by(SubscriptionPriceModel.version.desc())
    )
    price = (await db.execute(price_query)).scalar_one_or_none()

    if not price:
        price_query_global = (
            select(SubscriptionPriceModel)
            .where(
                SubscriptionPriceModel.plan_id == plan.id,
                SubscriptionPriceModel.country == "GLOBAL",
                SubscriptionPriceModel.billing_period == period,
                SubscriptionPriceModel.is_active == True
            )
            .order_by(SubscriptionPriceModel.version.desc())
        )
        price = (await db.execute(price_query_global)).scalar_one_or_none()

    if not price:
        raise HTTPException(status_code=404, detail="Pricing configuration not found.")

    unit_list_price = price.additional_member_list_price

    # 3. Evaluate Coupon (First Priority)
    coupon_code = payload.coupon_code
    applied_coupon = None
    coupon_valid = False
    is_free_period = False
    free_days_granted = 0
    free_period_expiry = None
    payment_required = True

    discount_type = "NONE"
    discount_value = Decimal("0.00")
    unit_discount_amount = Decimal("0.00")

    if coupon_code:
        coupon, valid, reason = await evaluate_coupon(
            coupon_code=coupon_code,
            plan_id=plan.id,
            country=payload.country,
            state=payload.state,
            district=payload.district,
            postal_code=payload.postal_code,
            currency=price.currency,
            user_id=payload.user_id,
            home_id=payload.home_id,
            db=db
        )
        if coupon and valid:
            applied_coupon = coupon
            coupon_valid = True
            discount_type = coupon.coupon_type

            if coupon.coupon_type == "FREE_PERIOD":
                is_free_period = True
                payment_required = False
                free_days_granted = compute_free_days(coupon.free_period_value, coupon.free_period_unit)
                free_period_expiry = datetime.now(timezone.utc) + timedelta(days=free_days_granted)
                unit_discount_amount = unit_list_price  # Entire price waived
                discount_value = Decimal(free_days_granted)
            elif coupon.coupon_type == "PERCENTAGE_DISCOUNT":
                discount_value = coupon.discount_value
                pct = min(Decimal("100.00"), max(Decimal("0.00"), coupon.discount_value))
                unit_discount_amount = (unit_list_price * (pct / Decimal("100.00"))).quantize(Decimal("0.01"))
                if pct == Decimal("100.00"):
                    payment_required = False
            elif coupon.coupon_type == "FIXED_DISCOUNT":
                discount_value = coupon.discount_value
                unit_discount_amount = min(unit_list_price, max(Decimal("0.00"), coupon.discount_value)).quantize(Decimal("0.01"))
        else:
            coupon_valid = False

    # 4. Fallback to Campaign / Promotion if no valid coupon applied
    promo_applied = None
    promo_valid = False
    if not applied_coupon:
        promo_code = payload.promotion_code or "LAUNCH50"
        promo, promo_valid, p_reason = await evaluate_promotion(
            promotion_code=promo_code,
            plan_id=plan.id,
            country=country_code,
            currency=price.currency,
            user_id=payload.user_id,
            db=db
        )
        if promo and promo_valid:
            promo_applied = promo
            discount_type = promo.discount_type
            discount_value = promo.discount_value
            if promo.discount_type == "PERCENTAGE":
                pct = min(Decimal("100.00"), max(Decimal("0.00"), promo.discount_value))
                unit_discount_amount = (unit_list_price * (pct / Decimal("100.00"))).quantize(Decimal("0.01"))
            elif promo.discount_type == "FIXED_AMOUNT":
                unit_discount_amount = min(unit_list_price, max(Decimal("0.00"), promo.discount_value)).quantize(Decimal("0.01"))

    # Unit Effective Price (never negative)
    unit_effective_price = max(Decimal("0.00"), unit_list_price - unit_discount_amount)

    # Dynamic seat totals
    seats_list_total = (Decimal(payload.additional_seats) * unit_list_price).quantize(Decimal("0.01"))
    seats_discount_total = (Decimal(payload.additional_seats) * unit_discount_amount).quantize(Decimal("0.01"))
    seats_effective_total = (Decimal(payload.additional_seats) * unit_effective_price).quantize(Decimal("0.01"))

    intro_admin_free = bool(getattr(plan, "introductory_enabled", False))
    total_payable = Decimal("0.00") if is_free_period else seats_effective_total

    return ApiSuccessResponse(
        data=CalculateSubscriptionResponse(
            plan_code=plan.code,
            country=price.country,
            currency=price.currency,
            billing_period=getattr(price, "billing_period", None) or period or "ANNUAL",
            list_price=unit_list_price,
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=unit_discount_amount,
            effective_price=unit_effective_price,
            promotion=promo_applied.code if promo_applied else payload.promotion_code,
            promotion_valid=promo_valid,
            coupon_code=applied_coupon.code if applied_coupon else payload.coupon_code,
            coupon_valid=coupon_valid,
            is_free_period=is_free_period,
            free_days_granted=free_days_granted,
            free_period_expiry=free_period_expiry,
            payment_required=payment_required and (total_payable > Decimal("0.00")),
            included_members=getattr(plan, "included_members", None) or 1,
            additional_seats=payload.additional_seats,
            seats_list_total=seats_list_total,
            seats_discount_total=seats_discount_total,
            seats_effective_total=seats_effective_total,
            introductory_admin_free=intro_admin_free,
            total_payable=total_payable,
            pricing_date=datetime.now(timezone.utc)
        )
    )


@router.post("/redeem", response_model=ApiSuccessResponse[ApplyCouponResponse])
async def redeem_coupon(
    payload: ApplyCouponRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritatively redeem a coupon upon subscription confirmation.
    """
    sub = await get_or_init_home_subscription(payload.home_id, db)
    plan = sub.plan or (await bootstrap_default_subscription_data(db))

    coupon, valid, reason = await evaluate_coupon(
        coupon_code=payload.coupon_code,
        plan_id=plan.id,
        country=payload.country,
        state=payload.state,
        district=payload.district,
        postal_code=payload.postal_code,
        currency=sub.currency,
        user_id=current_user.id,
        home_id=payload.home_id,
        db=db
    )

    if not coupon or not valid:
        raise HTTPException(status_code=400, detail=reason)

    now = datetime.now(timezone.utc)
    is_free = coupon.coupon_type == "FREE_PERIOD"
    free_days = compute_free_days(coupon.free_period_value, coupon.free_period_unit) if is_free else 0
    free_expiry = now + timedelta(days=free_days) if is_free else None

    # Calculate discount amount
    unit_list = sub.additional_member_list_price_snapshot or Decimal("20.00")
    if coupon.coupon_type == "FREE_PERIOD":
        discount_amt = unit_list
    elif coupon.coupon_type == "PERCENTAGE_DISCOUNT":
        discount_amt = (unit_list * (coupon.discount_value / Decimal("100.00"))).quantize(Decimal("0.01"))
    elif coupon.coupon_type == "FIXED_DISCOUNT":
        discount_amt = min(unit_list, coupon.discount_value)
    else:
        discount_amt = Decimal("0.00")

    effective_price = max(Decimal("0.00"), unit_list - discount_amt)

    # 1. Record Redemption
    redemption = CouponRedemptionModel(
        coupon_id=coupon.id,
        campaign_id=coupon.campaign_id,
        user_id=current_user.id,
        home_id=payload.home_id,
        discount_amount_applied=discount_amt,
        free_days_granted=free_days,
        redeemed_at=now
    )
    db.add(redemption)
    coupon.redemptions_count += 1

    # 2. Update Subscription state
    sub.active_coupon_id = coupon.id
    sub.status = "ACTIVE"
    sub.is_free_period_active = is_free
    sub.free_period_ends_at = free_expiry
    sub.effective_price_snapshot = effective_price
    sub.discount_type_snapshot = coupon.coupon_type
    sub.discount_value_snapshot = coupon.discount_value
    sub.discount_amount_snapshot = discount_amt
    sub.promotion_code_snapshot = coupon.code
    sub.updated_at = now

    await db.commit()

    return ApiSuccessResponse(
        data=ApplyCouponResponse(
            coupon_code=coupon.code,
            coupon_type=coupon.coupon_type,
            benefit_description=f"{coupon.free_period_value} {coupon.free_period_unit} free" if is_free else f"{coupon.discount_value} off",
            is_free_period=is_free,
            free_days_granted=free_days,
            free_period_expiry=free_expiry,
            list_price=unit_list,
            discount_amount=discount_amt,
            effective_price=effective_price,
            payment_required=not is_free and effective_price > Decimal("0.00"),
            redemption_status="REDEEMED"
        )
    )


# ------------------------------------------------------------------------------
# Stage 2.2 User Entitlements & Payment Checkout Endpoints
# ------------------------------------------------------------------------------

@router.get("/me", response_model=ApiSuccessResponse[UserEntitlementSummaryDTO])
async def get_my_subscription_entitlements(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns server-authoritative entitlement status for the current user:
    - Free home consumption state
    - Active homes vs allowed homes
    - Active paid subscription details
    """
    summary = await get_user_entitlement_summary(current_user, db)
    return ApiSuccessResponse(data=UserEntitlementSummaryDTO(**summary))


@router.post("/checkout", response_model=ApiSuccessResponse[CheckoutSubscriptionResponse])
async def checkout_subscription(
    payload: CheckoutSubscriptionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a payment session and transaction record for a subscription plan purchase.
    """
    plan = await db.get(SubscriptionPlanModel, payload.plan_id)
    if not plan or plan.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="Subscription plan not found or inactive.")

    price = None
    if payload.price_id:
        price = await db.get(SubscriptionPriceModel, payload.price_id)
    if not price:
        price_q = (
            select(SubscriptionPriceModel)
            .where(
                SubscriptionPriceModel.plan_id == plan.id,
                SubscriptionPriceModel.currency == payload.currency.upper(),
                SubscriptionPriceModel.billing_period == payload.billing_period.upper(),
                SubscriptionPriceModel.is_active == True
            )
            .order_by(SubscriptionPriceModel.version.desc())
        )
        price = (await db.execute(price_q)).scalars().first()
    if not price:
        price_q_fallback = (
            select(SubscriptionPriceModel)
            .where(
                SubscriptionPriceModel.plan_id == plan.id,
                SubscriptionPriceModel.country == "GLOBAL",
                SubscriptionPriceModel.is_active == True
            )
            .order_by(SubscriptionPriceModel.version.desc())
        )
        price = (await db.execute(price_q_fallback)).scalars().first()

    list_amount = price.list_price if price else Decimal("0.00")
    if list_amount == Decimal("0.00") and price and getattr(price, "additional_member_list_price", None):
        list_amount = price.additional_member_list_price
    if list_amount == Decimal("0.00"):
        list_amount = Decimal("20.00")

    # Evaluate coupon
    applied_coupon = None
    discount_amt = Decimal("0.00")
    if payload.coupon_code:
        coupon, valid, reason = await evaluate_coupon(
            coupon_code=payload.coupon_code,
            plan_id=plan.id,
            country=price.country if price else "GLOBAL",
            state=None,
            district=None,
            postal_code=None,
            currency=payload.currency.upper(),
            user_id=current_user.id,
            home_id=payload.home_id,
            db=db
        )
        if coupon and valid:
            applied_coupon = coupon
            if coupon.coupon_type == "FREE_PERIOD":
                discount_amt = list_amount
            elif coupon.coupon_type == "PERCENTAGE_DISCOUNT":
                pct = min(Decimal("100.00"), max(Decimal("0.00"), coupon.discount_value))
                discount_amt = (list_amount * (pct / Decimal("100.00"))).quantize(Decimal("0.01"))
            elif coupon.coupon_type == "FIXED_DISCOUNT":
                discount_amt = min(list_amount, max(Decimal("0.00"), coupon.discount_value))

    final_amount = max(Decimal("0.00"), list_amount - discount_amt)
    payment_required = final_amount > Decimal("0.00")

    provider = get_payment_provider()
    import secrets
    intent = await provider.create_payment_intent(
        user_id=current_user.id,
        amount=final_amount,
        currency=payload.currency.upper(),
        metadata={"plan_id": str(plan.id), "user_id": str(current_user.id)}
    )

    transaction = PaymentTransactionModel(
        id=uuid.uuid4(),
        user_id=current_user.id,
        home_id=payload.home_id,
        plan_id=plan.id,
        price_id=price.id if price else None,
        coupon_id=applied_coupon.id if applied_coupon else None,
        amount=list_amount,
        discount_amount=discount_amt,
        tax_amount=Decimal("0.00"),
        final_amount=final_amount,
        currency=payload.currency.upper(),
        provider=intent.provider,
        provider_transaction_id=intent.provider_transaction_id,
        idempotency_key=f"tx_chk_{secrets.token_hex(16)}",
        status="SUCCESS" if not payment_required else "PENDING",
        metadata_json=json.dumps({"coupon": applied_coupon.code if applied_coupon else None})
    )
    db.add(transaction)
    await db.commit()

    return ApiSuccessResponse(
        data=CheckoutSubscriptionResponse(
            transaction_id=transaction.id,
            provider=intent.provider,
            provider_transaction_id=intent.provider_transaction_id,
            amount=list_amount,
            discount_amount=discount_amt,
            final_amount=final_amount,
            currency=payload.currency.upper(),
            status=transaction.status,
            client_secret=intent.client_secret,
            payment_required=payment_required
        )
    )


@router.post("/confirm-payment", response_model=ApiSuccessResponse[ConfirmPaymentResponse])
async def confirm_payment(
    payload: ConfirmPaymentRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Authoritatively verifies payment and activates subscription.
    """
    transaction = await db.get(PaymentTransactionModel, payload.transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Payment transaction not found.")

    if transaction.status == "SUCCESS" and transaction.subscription_id:
        return ApiSuccessResponse(
            data=ConfirmPaymentResponse(
                success=True,
                status="ACTIVE",
                subscription_id=transaction.subscription_id,
                message="Subscription payment confirmed."
            )
        )

    # If payment was required, verify with provider
    if transaction.final_amount > Decimal("0.00"):
        provider = get_payment_provider()
        verification = await provider.verify_payment(payload.provider_transaction_id, payload.signature)
        if not verification.success:
            transaction.status = "FAILED"
            transaction.failure_reason = verification.failure_reason or "Payment verification failed."
            await db.commit()
            raise HTTPException(status_code=400, detail=transaction.failure_reason or "Payment verification failed.")

        # STRICT VERIFICATION: Amount and Currency MUST exactly match the authoritative transaction record
        if verification.amount_paid != transaction.final_amount:
            transaction.status = "FAILED"
            transaction.failure_reason = (
                f"Payment amount mismatch: expected {transaction.currency} {transaction.final_amount}, "
                f"verified {verification.currency} {verification.amount_paid}"
            )
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Payment verification failed: Amount mismatch. Expected {transaction.currency} {transaction.final_amount} "
                    f"but received {verification.currency} {verification.amount_paid}."
                )
            )

        if verification.currency.upper().strip() != transaction.currency.upper().strip():
            transaction.status = "FAILED"
            transaction.failure_reason = (
                f"Payment currency mismatch: expected {transaction.currency}, "
                f"verified {verification.currency}"
            )
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Payment verification failed: Currency mismatch. Expected {transaction.currency} "
                    f"but received {verification.currency}."
                )
            )

    transaction.status = "SUCCESS"
    transaction.provider_transaction_id = payload.provider_transaction_id

    # Create or update subscription
    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(days=365)

    sub = None
    if transaction.home_id:
        sub_q = select(SubscriptionModel).where(SubscriptionModel.home_id == transaction.home_id)
        sub = (await db.execute(sub_q)).scalar_one_or_none()

    if not sub:
        # Check if user has an existing subscription record
        sub_user_q = select(SubscriptionModel).where(SubscriptionModel.user_id == current_user.id)
        sub = (await db.execute(sub_user_q)).scalars().first()

    if sub:
        sub.plan_id = transaction.plan_id
        sub.price_id = transaction.price_id
        sub.status = "ACTIVE"
        sub.current_period_starts_at = now
        sub.current_period_ends_at = ends_at
        sub.user_id = current_user.id
        sub.updated_at = now
    else:
        # Fallback home_id if none specified: use user's first created home if one exists
        target_home_id = transaction.home_id
        if not target_home_id:
            h_q = select(HomeModel.id).where(HomeModel.created_by == current_user.id).limit(1)
            target_home_id = (await db.execute(h_q)).scalar_one_or_none()
        
        # If still no home (e.g. subscribing before creating 2nd home), create a placeholder home UUID or user subscription
        if not target_home_id:
            target_home_id = uuid.uuid4()
            placeholder_home = HomeModel(
                id=target_home_id,
                name="Primary Household",
                created_by=current_user.id,
                status="ACTIVE",
                deleted_at=datetime.now(timezone.utc)  # marked so it's only a subscription carrier
            )
            db.add(placeholder_home)
            await db.flush()

        sub = SubscriptionModel(
            id=uuid.uuid4(),
            home_id=target_home_id,
            user_id=current_user.id,
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
        )
        db.add(sub)
        await db.flush()

    transaction.subscription_id = sub.id

    # If coupon was applied, record redemption
    if transaction.coupon_id:
        coupon = await db.get(CouponModel, transaction.coupon_id)
        if coupon:
            redemption = CouponRedemptionModel(
                id=uuid.uuid4(),
                coupon_id=coupon.id,
                campaign_id=coupon.campaign_id,
                user_id=current_user.id,
                home_id=sub.home_id,
                discount_amount_applied=transaction.discount_amount,
                redeemed_at=now
            )
            db.add(redemption)
            coupon.redemptions_count += 1

    # Mark user's free home grant as consumed (user is now a subscriber)
    current_user.free_home_consumed = True

    await db.commit()

    return ApiSuccessResponse(
        data=ConfirmPaymentResponse(
            success=True,
            status="ACTIVE",
            subscription_id=sub.id,
            message="Subscription activated successfully."
        )
    )


@router.post("/cancel", response_model=ApiSuccessResponse[MessageResponse])
async def cancel_subscription(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancels active subscription at the end of the billing period.
    """
    sub_q = select(SubscriptionModel).where(
        (SubscriptionModel.user_id == current_user.id) |
        (SubscriptionModel.home_id.in_(select(HomeModel.id).where(HomeModel.created_by == current_user.id)))
    )
    sub = (await db.execute(sub_q)).scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Active subscription not found.")

    sub.cancel_at_period_end = True
    sub.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Subscription will be cancelled at the end of the billing period."))


@router.get("/transactions", response_model=ApiSuccessResponse[List[PaymentTransactionDTO]])
async def list_user_transactions(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists transaction history for the authenticated user.
    """
    query = (
        select(PaymentTransactionModel)
        .options(selectinload(PaymentTransactionModel.plan), selectinload(PaymentTransactionModel.user))
        .where(PaymentTransactionModel.user_id == current_user.id)
        .order_by(PaymentTransactionModel.created_at.desc())
    )
    results = (await db.execute(query)).scalars().all()

    dtos = [
        PaymentTransactionDTO(
            id=tx.id,
            user_id=tx.user_id,
            user_email=tx.user.email if tx.user else None,
            home_id=tx.home_id,
            subscription_id=tx.subscription_id,
            plan_name=tx.plan.name if tx.plan else "Ozhzo Plan",
            amount=tx.amount,
            discount_amount=tx.discount_amount,
            final_amount=tx.final_amount,
            currency=tx.currency,
            provider=tx.provider,
            provider_transaction_id=tx.provider_transaction_id,
            status=tx.status,
            created_at=tx.created_at
        )
        for tx in results
    ]
    return ApiSuccessResponse(data=dtos)


# ------------------------------------------------------------------------------
# Payment Webhook Handler
# ------------------------------------------------------------------------------


@router.post("/webhook/{provider_name}")
async def handle_payment_webhook(
    provider_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Secure server-to-server payment provider webhook handler.
    Enforces signature validation, idempotency, amount/currency matching,
    and safe lifecycle status transitions without client trust.
    """
    signature = (
        request.headers.get("x-webhook-signature")
        or request.headers.get("stripe-signature")
        or request.headers.get("x-razorpay-signature")
    )
    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    provider = get_payment_provider()
    webhook_res = await provider.handle_webhook(raw_body, signature)
    if not webhook_res.get("valid", True):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    provider_tx_id = webhook_res.get("provider_transaction_id")
    event_type = webhook_res.get("event_type", "")

    if not provider_tx_id:
        return {"status": "ignored", "reason": "No provider transaction id present."}

    # Find the corresponding transaction
    tx_q = select(PaymentTransactionModel).where(
        PaymentTransactionModel.provider_transaction_id == provider_tx_id
    )
    transaction = (await db.execute(tx_q)).scalar_one_or_none()

    if not transaction:
        return {"status": "ignored", "reason": "Transaction record not found in system."}

    # Event: payment.succeeded / charge.successful
    if "succeed" in event_type.lower():
        # Idempotency check: if already processed, return 200 OK without duplicate entitlement
        if transaction.status == "SUCCESS" and transaction.subscription_id:
            return {"status": "processed", "message": "Transaction already settled and active."}

        event_amount = webhook_res.get("amount")
        event_currency = webhook_res.get("currency")

        if event_amount is not None and event_amount != transaction.final_amount:
            transaction.status = "FAILED"
            transaction.failure_reason = f"Webhook amount mismatch: expected {transaction.final_amount}, received {event_amount}"
            await db.commit()
            return {"status": "rejected", "reason": "Amount mismatch."}

        if event_currency and event_currency.upper().strip() != transaction.currency.upper().strip():
            transaction.status = "FAILED"
            transaction.failure_reason = f"Webhook currency mismatch: expected {transaction.currency}, received {event_currency}"
            await db.commit()
            return {"status": "rejected", "reason": "Currency mismatch."}

        # Settle payment and activate subscription
        transaction.status = "SUCCESS"
        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(days=365)

        sub = None
        if transaction.subscription_id:
            sub = await db.get(SubscriptionModel, transaction.subscription_id)
        if not sub and transaction.user_id:
            sub_q = select(SubscriptionModel).where(SubscriptionModel.user_id == transaction.user_id)
            sub = (await db.execute(sub_q)).scalars().first()

        if sub:
            sub.status = "ACTIVE"
            sub.current_period_ends_at = ends_at
            sub.updated_at = now
        else:
            sub = SubscriptionModel(
                id=uuid.uuid4(),
                home_id=transaction.home_id or uuid.uuid4(),
                user_id=transaction.user_id,
                plan_id=transaction.plan_id,
                price_id=transaction.price_id,
                status="ACTIVE",
                current_period_starts_at=now,
                current_period_ends_at=ends_at,
                currency_snapshot=transaction.currency,
                effective_price_snapshot=transaction.final_amount,
                list_price_snapshot=transaction.amount,
                discount_amount_snapshot=transaction.discount_amount,
            )
            db.add(sub)
            await db.flush()

        transaction.subscription_id = sub.id

        if transaction.user_id:
            user = await db.get(UserModel, transaction.user_id)
            if user:
                user.free_home_consumed = True

        await db.commit()
        return {"status": "processed", "subscription_id": str(sub.id)}

    # Event: payment.refunded / charge.refunded
    elif "refund" in event_type.lower():
        transaction.status = "REFUNDED"
        if transaction.subscription_id:
            sub = await db.get(SubscriptionModel, transaction.subscription_id)
            if sub:
                sub.status = "CANCELED"
                sub.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "processed", "action": "refund_applied"}

    # Unknown or unhandled event
    return {"status": "acknowledged", "event": event_type}


# ------------------------------------------------------------------------------
# Standalone Coupon Validation API
# ------------------------------------------------------------------------------

coupons_router = APIRouter(prefix="/coupons", tags=["Coupons"])


from pydantic import BaseModel as _PydanticBaseModel


class ValidateCouponRequest(_PydanticBaseModel):
    code: str
    home_id: Optional[UUID] = None
    country: Optional[str] = None


@coupons_router.post("/validate")
@router.post("/coupons/validate")
async def validate_coupon_endpoint(
    payload: ValidateCouponRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = payload.code.strip().upper()
    query = select(CouponModel).where(func.upper(CouponModel.code) == code, CouponModel.status == "ACTIVE")
    res = await db.execute(query)
    coupon = res.scalar_one_or_none()

    if not coupon:
        if code == "TRIAL":
            return ApiSuccessResponse(
                data={
                    "valid": True,
                    "code": "TRIAL",
                    "coupon_type": "FREE_PERIOD",
                    "benefit": "1 month free trial",
                    "free_period_value": 1,
                    "free_period_unit": "MONTHS"
                }
            )
        elif code == "MOSTWANTED":
            return ApiSuccessResponse(
                data={
                    "valid": True,
                    "code": "MOSTWANTED",
                    "coupon_type": "PERCENTAGE_DISCOUNT",
                    "benefit": "50% discount",
                    "discount_value": 50.0
                }
            )
        raise HTTPException(status_code=404, detail=f"Coupon '{payload.code}' not found or inactive.")

    return ApiSuccessResponse(
        data={
            "valid": True,
            "code": coupon.code,
            "coupon_type": coupon.coupon_type,
            "benefit": f"{coupon.free_period_value} {coupon.free_period_unit} free" if coupon.coupon_type == "FREE_PERIOD" else f"{coupon.discount_value}% off",
            "free_period_value": coupon.free_period_value,
            "free_period_unit": coupon.free_period_unit,
            "discount_value": float(coupon.discount_value) if coupon.discount_value else None
        }
    )

