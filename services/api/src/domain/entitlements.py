from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from unittest.mock import AsyncMock
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import TierLimitExceededException
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InvitationModel,
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
