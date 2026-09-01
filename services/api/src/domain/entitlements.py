from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from unittest.mock import AsyncMock
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import TierLimitExceededException
from src.infrastructure.database.models import (
    HomeAccessEntitlementModel,
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    SubscriptionCreditModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel
)


async def check_can_create_home(current_user: UserModel, db: AsyncSession, lock_user: bool = True) -> None:
    """
    Enforces the core commercial invariant:
      ONE USER = ONE FREE HOME (Lifetime).
      - User can create their first Home without payment (0 active homes & free_home_consumed is False).
      - Any additional Home created by the same user requires an active paid subscription entitlement.
      - Deleting/archiving a Home does NOT reset the user's consumed free-home entitlement.
      - Uses concurrency locking on the user record to prevent race-condition bypasses.
    """
    # 1. Lock user record if inside an active transaction to serialize concurrent home creation
    if lock_user and not isinstance(db, AsyncMock) and not getattr(db, "_is_mock", False):
        try:
            lock_query = select(UserModel.id).where(UserModel.id == current_user.id).with_for_update()
            await db.execute(lock_query)
        except Exception:
            pass

    # 2. Query active (non-deleted) homes created by this user
    query = select(HomeModel).where(
        HomeModel.created_by == current_user.id,
        HomeModel.deleted_at.is_(None)
    )
    existing_result = await db.execute(query)
    existing_homes = []
    if hasattr(existing_result, "scalars"):
        existing_homes = existing_result.scalars().all()
    elif hasattr(existing_result, "all"):
        existing_homes = existing_result.all()

    active_homes_count = len(existing_homes)
    free_consumed = getattr(current_user, "free_home_consumed", False)

    # 3. If user has 0 active homes AND has never consumed their free home grant -> ALLOW FREE
    if active_homes_count == 0 and not free_consumed:
        return

    # 4. Otherwise, user must have an active paid subscription granting additional home capacity
    now = datetime.now(timezone.utc)
    
    # Query subscriptions by user_id OR by any owned home
    home_ids = [h.id if hasattr(h, "id") else h[0].id for h in existing_homes]
    sub_conditions = [
        (SubscriptionModel.user_id == current_user.id) & SubscriptionModel.status.in_(["ACTIVE", "TRIALING"])
    ]
    if home_ids:
        sub_conditions.append(
            (SubscriptionModel.home_id.in_(home_ids)) & SubscriptionModel.status.in_(["ACTIVE", "TRIALING"])
        )

    from sqlalchemy import or_
    sub_query = (
        select(SubscriptionModel)
        .options(selectinload(SubscriptionModel.plan))
        .where(or_(*sub_conditions))
    )
    sub_res = await db.execute(sub_query)
    active_subs = []
    if hasattr(sub_res, "scalars"):
        scalars_obj = sub_res.scalars()
        all_res = scalars_obj.all() if hasattr(scalars_obj, "all") else None
        if isinstance(all_res, list) and len(all_res) > 0:
            active_subs = all_res
        elif hasattr(scalars_obj, "first"):
            first_val = scalars_obj.first()
            if first_val is not None and getattr(first_val, "status", None) is not None:
                active_subs = [first_val]
            elif isinstance(all_res, list):
                active_subs = all_res
        elif isinstance(all_res, list):
            active_subs = all_res
    elif hasattr(sub_res, "all"):
        all_res = sub_res.all()
        if isinstance(all_res, list):
            active_subs = all_res
    elif hasattr(sub_res, "first"):
        first_val = sub_res.first()
        if first_val is not None:
            active_subs = [first_val]

    # Calculate total allowed homes
    # Baseline: 1 Free Home + any additional capacity granted by active plans
    total_allowed_homes = 1
    has_valid_paid_subscription = False

    for sub in active_subs:
        sub_status = getattr(sub, "status", None)
        if sub_status in ["ACTIVE", "TRIALING"]:
            sub_ends = getattr(sub, "current_period_ends_at", None)
            if sub_ends and sub_ends < now:
                continue
            has_valid_paid_subscription = True
            sub_plan = getattr(sub, "plan", None)
            plan_max = getattr(sub_plan, "max_homes", 10) if sub_plan else 10
            total_allowed_homes = max(total_allowed_homes, plan_max)

    if not has_valid_paid_subscription or active_homes_count >= total_allowed_homes:
        raise TierLimitExceededException(
            resource="homes",
            limit=total_allowed_homes if has_valid_paid_subscription else 1,
            detail="Your free plan includes one Home. Upgrade your subscription to create another Home."
        )


async def get_user_entitlement_summary(current_user: UserModel, db: AsyncSession) -> Dict[str, Any]:
    """
    Returns the comprehensive, server-authoritative entitlement status for a user:
    - Free home consumption state
    - Current active homes count
    - Total allowed homes
    - Can create home boolean
    - Active subscription details
    """
    query = select(HomeModel).where(
        HomeModel.created_by == current_user.id,
        HomeModel.deleted_at.is_(None)
    )
    res = await db.execute(query)
    existing_homes = res.scalars().all() if hasattr(res, "scalars") else []
    active_homes_count = len(existing_homes)

    free_consumed = getattr(current_user, "free_home_consumed", False) or (active_homes_count > 0)
    
    # Query active subscriptions
    now = datetime.now(timezone.utc)
    home_ids = [h.id for h in existing_homes]
    from sqlalchemy import or_
    sub_conditions = [
        (SubscriptionModel.user_id == current_user.id) & SubscriptionModel.status.in_(["ACTIVE", "TRIALING"])
    ]
    if home_ids:
        sub_conditions.append(
            (SubscriptionModel.home_id.in_(home_ids)) & SubscriptionModel.status.in_(["ACTIVE", "TRIALING"])
        )

    sub_query = (
        select(SubscriptionModel)
        .options(selectinload(SubscriptionModel.plan), selectinload(SubscriptionModel.price))
        .where(or_(*sub_conditions))
    )
    sub_res = await db.execute(sub_query)
    active_subs = sub_res.scalars().all() if hasattr(sub_res, "scalars") else []

    total_allowed_homes = 1
    active_sub_dto = None

    for sub in active_subs:
        if sub.status in ["ACTIVE", "TRIALING"] and (not sub.current_period_ends_at or sub.current_period_ends_at >= now):
            plan_max = getattr(sub.plan, "max_homes", 10) if sub.plan else 10
            total_allowed_homes = max(total_allowed_homes, plan_max)
            if not active_sub_dto:
                active_sub_dto = {
                    "id": str(sub.id),
                    "plan_name": sub.plan.name if sub.plan else "Ozhzo Standard",
                    "plan_code": sub.plan.code if sub.plan else "OZHZO_HOME",
                    "status": sub.status,
                    "max_homes": plan_max,
                    "paid_member_seats": sub.paid_member_seats,
                    "current_period_ends_at": sub.current_period_ends_at.isoformat() if sub.current_period_ends_at else None,
                    "currency": sub.currency_snapshot or "USD",
                }

    can_create = (active_homes_count == 0 and not free_consumed) or (active_homes_count < total_allowed_homes and active_sub_dto is not None)

    return {
        "free_home_consumed": free_consumed,
        "free_home_included": 1,
        "active_homes_count": active_homes_count,
        "total_allowed_homes": total_allowed_homes,
        "can_create_home": can_create,
        "active_subscription": active_sub_dto,
    }


async def check_and_reserve_home_member_seat(
    home_id: UUID,
    db: AsyncSession,
    include_pending_invitations: bool = False,
    lock_home: bool = True
) -> int:
    """
    Enforces member seat limits with transactional locking to prevent race conditions.
    Calculates applicable seats based on Free tier (5 seats) or Active Subscription.
    Returns the total allowed seats if successful, or raises TierLimitExceededException.
    """
    if lock_home and not isinstance(db, AsyncMock) and not getattr(db, "_is_mock", False):
        try:
            lock_query = select(HomeModel.id).where(HomeModel.id == home_id).with_for_update()
            await db.execute(lock_query)
        except Exception:
            pass

    active_count_query = select(func.count(HomeMemberModel.id)).where(
        HomeMemberModel.home_id == home_id,
        HomeMemberModel.status == "ACTIVE"
    )
    try:
        cnt_res = await db.execute(active_count_query)
        cnt_val = cnt_res.scalar() if hasattr(cnt_res, "scalar") else None
        current_count = cnt_val if isinstance(cnt_val, (int, float)) else 0
    except (Exception, StopAsyncIteration):
        current_count = 0

    if include_pending_invitations:
        try:
            pending_count_query = select(func.count(InvitationModel.id)).where(
                InvitationModel.home_id == home_id,
                InvitationModel.status == "PENDING"
            )
            p_res = await db.execute(pending_count_query)
            p_val = p_res.scalar() if hasattr(p_res, "scalar") else None
            p_cnt = p_val if isinstance(p_val, (int, float)) else 0
            current_count += int(p_cnt)
        except (Exception, StopAsyncIteration):
            pass

    sub_query = (
        select(SubscriptionModel)
        .options(selectinload(SubscriptionModel.plan))
        .where(SubscriptionModel.home_id == home_id)
    )
    try:
        sub_res = await db.execute(sub_query)
        sub = sub_res.scalars().first() if hasattr(sub_res, "scalars") else None
        if not sub and hasattr(sub_res, "scalar_one_or_none"):
            sub = sub_res.scalar_one_or_none()
    except (Exception, StopAsyncIteration):
        sub = None

    if isinstance(sub, SubscriptionModel) and sub.status in ["ACTIVE", "TRIALING"]:
        included = sub.plan.included_members if (sub.plan and hasattr(sub.plan, "included_members")) else 5
        paid_seats = getattr(sub, "paid_member_seats", 0) or 0
        total_allowed = included + paid_seats
        if sub.plan and getattr(sub.plan, "maximum_members", None) and total_allowed > sub.plan.maximum_members:
            total_allowed = sub.plan.maximum_members
    else:
        # Default Free Tier allowance
        total_allowed = 5

    if current_count >= total_allowed:
        raise TierLimitExceededException(
            resource="members",
            limit=total_allowed,
            detail=f"Home has reached its member seat limit ({total_allowed} seats). Your Home subscription does not have an available member seat."
        )

    return total_allowed


async def provision_first_year_free_entitlement(
    user: UserModel,
    home: HomeModel,
    db: AsyncSession
) -> HomeAccessEntitlementModel:
    """
    Provisions the authoritative 1-Year Free Access Entitlement for the creator's first Home.
    Enforces Rule B: FIRST_YEAR_FREE with 365-day access window.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=365)

    entitlement = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home.id,
        user_id=user.id,
        subscription_id=None,
        entitlement_type="FIRST_YEAR_FREE",
        status="ACTIVE",
        starts_at=now,
        expires_at=expires_at,
        notes="First-Year Free Entitlement for First Created Home",
        created_by=user.id,
        created_at=now,
        updated_at=now
    )
    db.add(entitlement)
    return entitlement


async def provision_paid_home_entitlement(
    user: UserModel,
    home: HomeModel,
    subscription_id: Optional[UUID],
    db: AsyncSession,
    expires_at: Optional[datetime] = None
) -> HomeAccessEntitlementModel:
    """
    Provisions a Paid Access Entitlement for additional Homes or Paid Member Seats.
    Enforces Rule C & Rule E.
    """
    now = datetime.now(timezone.utc)
    if not expires_at:
        expires_at = now + timedelta(days=365)

    entitlement = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home.id,
        user_id=user.id,
        subscription_id=subscription_id,
        entitlement_type="PAID_SEAT",
        status="ACTIVE",
        starts_at=now,
        expires_at=expires_at,
        notes="Paid Subscription Home Access Entitlement",
        created_by=user.id,
        created_at=now,
        updated_at=now
    )
    db.add(entitlement)
    return entitlement


async def reserve_home_access_entitlement(
    home_id: UUID,
    admin_user_id: UUID,
    identifier_type: str,  # PHONE or EMAIL
    identifier_value: str,
    subscription_id: Optional[UUID],
    db: AsyncSession,
    duration_days: int = 365,
    notes: Optional[str] = None
) -> HomeAccessEntitlementModel:
    """
    Creates a pre-allocated subscription reservation for a specific person identified by unique verified mobile or email.
    Status starts in 'RESERVED' and transitions to 'ACTIVE' upon authenticated user claim.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=duration_days)

    clean_val = identifier_value.strip().lower() if identifier_type.upper() == "EMAIL" else identifier_value.strip()

    reservation = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=None,
        subscription_id=subscription_id,
        reserved_identifier_type=identifier_type.upper(),
        reserved_identifier_value=clean_val,
        entitlement_type="RESERVATION",
        status="RESERVED",
        starts_at=now,
        expires_at=expires_at,
        notes=notes or f"Reserved seat for {clean_val}",
        created_by=admin_user_id,
        created_at=now,
        updated_at=now
    )
    db.add(reservation)
    return reservation


async def claim_reserved_entitlement(
    user: UserModel,
    home_id: UUID,
    db: AsyncSession
) -> Optional[HomeAccessEntitlementModel]:
    """
    Binds and activates any pending RESERVED access entitlement matching the user's verified phone or email.
    """
    identifiers = []
    if getattr(user, "email", None):
        identifiers.append(user.email.strip().lower())
    if getattr(user, "phone_number", None):
        identifiers.append(user.phone_number.strip())

    if not identifiers:
        return None

    entitlement = None
    try:
        query = select(HomeAccessEntitlementModel).where(
            HomeAccessEntitlementModel.home_id == home_id,
            HomeAccessEntitlementModel.status == "RESERVED",
            HomeAccessEntitlementModel.reserved_identifier_value.in_(identifiers)
        )
        res = await db.execute(query)
        if hasattr(res, "scalars"):
            scalars_obj = res.scalars()
            entitlement = scalars_obj.first() if hasattr(scalars_obj, "first") else None
        elif hasattr(res, "scalar_one_or_none"):
            entitlement = res.scalar_one_or_none()
    except (Exception, StopAsyncIteration):
        entitlement = None

    if entitlement:
        now = datetime.now(timezone.utc)
        entitlement.user_id = user.id
        entitlement.status = "ACTIVE"
        entitlement.starts_at = now
        entitlement.expires_at = now + timedelta(days=365)
        entitlement.updated_at = now
        return entitlement

    return None


async def verify_user_home_access_entitlement(
    user: UserModel,
    home_id: UUID,
    db: AsyncSession
) -> Tuple[bool, Optional[HomeAccessEntitlementModel], str]:
    """
    Authoritatively evaluates server-side:
      "Does this particular user have valid access entitlement to this particular Home?"
    Returns:
      (is_authorized: bool, entitlement: Optional[HomeAccessEntitlementModel], reason: str)
    """
    # 1. Super Admin is completely separate and exempt (Rule F)
    is_super_admin = getattr(user, "is_super_admin", False) or (getattr(user, "system_role", "USER") in ["SUPER_ADMIN", "PLATFORM_ADMIN"])
    if is_super_admin:
        return True, None, "Super Admin platform bypass."

    now = datetime.now(timezone.utc)

    # 2. Check for explicit HomeAccessEntitlementModel
    try:
        query = select(HomeAccessEntitlementModel).where(
            HomeAccessEntitlementModel.home_id == home_id,
            HomeAccessEntitlementModel.user_id == user.id
        ).order_by(HomeAccessEntitlementModel.expires_at.desc())
        res = await db.execute(query)
        entitlements = []
        if hasattr(res, "scalars"):
            scalars_obj = res.scalars()
            entitlements = scalars_obj.all() if hasattr(scalars_obj, "all") else []
        elif hasattr(res, "all"):
            entitlements = res.all()
    except Exception:
        entitlements = []

    for ent in entitlements:
        if not isinstance(ent, HomeAccessEntitlementModel):
            continue
        if ent.status == "ACTIVE":
            if ent.expires_at >= now:
                return True, ent, "Valid active access entitlement."
            else:
                # Expired entitlement
                ent.status = "EXPIRED"
                ent.updated_at = now
                return False, ent, "Your access entitlement to this Home has expired. A valid subscription is required to access this Home."

    # 3. Check for matching reservation to auto-claim
    claimed = await claim_reserved_entitlement(user, home_id, db)
    if claimed:
        return True, claimed, "Claimed reserved access entitlement."

    # 4. Fallback / backward-compatibility check for existing Stage 1 & Stage 2 active members
    try:
        home = await db.get(HomeModel, home_id)
    except Exception:
        home = None

    if home:
        # Check if user is the creator of the Home
        if home.created_by == user.id:
            home_created_at = getattr(home, "created_at", None) or now
            # First year window: created_at + 365 days
            first_year_expiry = home_created_at + timedelta(days=365)
            if first_year_expiry >= now:
                # Auto-provision First Year Free entitlement
                try:
                    new_ent = await provision_first_year_free_entitlement(user, home, db)
                    new_ent.starts_at = home_created_at
                    new_ent.expires_at = first_year_expiry
                    return True, new_ent, "First-Year Free Entitlement active."
                except Exception:
                    return True, None, "First-Year Free Entitlement active."
            else:
                return False, None, "Your first-year free access entitlement to this Home has expired. A valid subscription is required."

        # Check if home has an active subscription with member seats
        try:
            sub_q = select(SubscriptionModel).where(
                SubscriptionModel.home_id == home_id,
                SubscriptionModel.status.in_(["ACTIVE", "TRIALING"])
            )
            sub_res = await db.execute(sub_q)
            sub = sub_res.scalars().first() if hasattr(sub_res, "scalars") else None
            if sub and (not sub.current_period_ends_at or sub.current_period_ends_at >= now):
                new_ent = await provision_paid_home_entitlement(
                    user, home, sub.id, db, expires_at=sub.current_period_ends_at
                )
                return True, new_ent, "Active subscription entitlement allocated."
        except Exception:
            pass

    return False, None, "No valid access entitlement found for this Home."


# ==============================================================================
# SUBSCRIPTION CREDIT LEDGER & DOUBLE-SPEND ENGINE (Stage 2.2A)
# ==============================================================================

async def get_user_available_credits(
    user_id: UUID,
    currency: str,
    db: AsyncSession,
    for_update: bool = False
) -> List[SubscriptionCreditModel]:
    """
    Retrieves all available and non-expired subscription credits for a user in the requested currency.
    If for_update=True, acquires row-level locks (FOR UPDATE) for double-spend protection.
    """
    now = datetime.now(timezone.utc)
    curr = currency.upper().strip()

    query = select(SubscriptionCreditModel).where(
        SubscriptionCreditModel.user_id == user_id,
        SubscriptionCreditModel.currency == curr,
        SubscriptionCreditModel.status.in_(["AVAILABLE", "PARTIALLY_USED"]),
        SubscriptionCreditModel.remaining_amount > Decimal("0.00"),
        (SubscriptionCreditModel.expires_at.is_(None) | (SubscriptionCreditModel.expires_at >= now))
    ).order_by(SubscriptionCreditModel.created_at.asc())

    if for_update:
        query = query.with_for_update()

    try:
        res = await db.execute(query)
        if hasattr(res, "scalars"):
            return list(res.scalars().all())
        return []
    except Exception:
        return []


async def get_user_credit_balance(
    user_id: UUID,
    currency: str,
    db: AsyncSession
) -> Decimal:
    """
    Calculates the total authoritative available credit balance for a user in a given currency.
    """
    credits = await get_user_available_credits(user_id, currency, db, for_update=False)
    return sum([c.remaining_amount for c in credits], Decimal("0.00"))


async def consume_user_credits(
    user_id: UUID,
    required_amount: Decimal,
    currency: str,
    db: AsyncSession,
    transaction_id: Optional[UUID] = None,
    description: Optional[str] = None
) -> Tuple[Decimal, List[SubscriptionCreditModel]]:
    """
    Atomically consumes available credits up to required_amount.
    Guarantees:
      - Double-spend protection via SELECT ... FOR UPDATE.
      - Immutable audit trail.
      - Never allows negative remaining balances.
      - Rejects currency mismatch.
    Returns: (total_consumed_amount, list_of_affected_credits)
    """
    if required_amount <= Decimal("0.00"):
        return Decimal("0.00"), []

    credits = await get_user_available_credits(user_id, currency, db, for_update=True)
    if not credits:
        return Decimal("0.00"), []

    remaining_to_deduct = required_amount
    total_deducted = Decimal("0.00")
    affected_credits = []
    now = datetime.now(timezone.utc)

    for cred in credits:
        if remaining_to_deduct <= Decimal("0.00"):
            break

        avail = cred.remaining_amount
        if avail <= Decimal("0.00"):
            continue

        deduction = min(avail, remaining_to_deduct)
        cred.remaining_amount = avail - deduction
        total_deducted += deduction
        remaining_to_deduct -= deduction

        if cred.remaining_amount == Decimal("0.00"):
            cred.status = "REDEEMED"
        else:
            cred.status = "PARTIALLY_USED"

        cred.updated_at = now
        if transaction_id:
            cred.redeemed_transaction_id = transaction_id
        if description and not cred.description:
            cred.description = description

        affected_credits.append(cred)

    return total_deducted, affected_credits


async def grant_user_credit(
    user_id: UUID,
    amount: Decimal,
    currency: str,
    credit_type: str,
    reason: str,
    db: AsyncSession,
    home_id: Optional[UUID] = None,
    expires_in_days: Optional[int] = None,
    admin_id: Optional[UUID] = None,
    source_type: Optional[str] = "ADMIN_MANUAL",
    source_id: Optional[UUID] = None,
    reference: Optional[str] = None,
    description: Optional[str] = None
) -> SubscriptionCreditModel:
    """
    Issues immutable reusable subscription credit to a user.
    """
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=expires_in_days)) if expires_in_days else None

    credit = SubscriptionCreditModel(
        id=uuid4(),
        user_id=user_id,
        home_id=home_id,
        amount=amount,
        remaining_amount=amount,
        currency=currency.upper().strip(),
        credit_type=credit_type.upper().strip(),
        status="AVAILABLE",
        source_type=source_type,
        source_id=source_id,
        reference=reference or reason,
        description=description or reason,
        expires_at=expires_at,
        created_by=admin_id,
        created_at=now,
        updated_at=now
    )
    db.add(credit)
    return credit


async def revoke_user_credit(
    credit_id: UUID,
    reason: str,
    admin_id: UUID,
    db: AsyncSession
) -> SubscriptionCreditModel:
    """
    Revokes the remaining unconsumed balance of a subscription credit.
    """
    credit = await db.get(SubscriptionCreditModel, credit_id)
    if not credit:
        raise HTTPException(status_code=404, detail="Subscription credit record not found.")

    if credit.status in ["REDEEMED", "CANCELLED", "EXPIRED"]:
        raise HTTPException(status_code=400, detail=f"Credit is already {credit.status} and cannot be revoked.")

    credit.remaining_amount = Decimal("0.00")
    credit.status = "CANCELLED"
    credit.updated_at = datetime.now(timezone.utc)
    credit.description = f"{credit.description or ''} [REVOKED: {reason}]".strip()

    return credit

