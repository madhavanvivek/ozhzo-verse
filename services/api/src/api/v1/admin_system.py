from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    HomeMemberModel,
    HomeModel,
    SubscriptionModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.admin import AdminAnalyticsSummaryDTO, AdminSystemConfigDTO

router = APIRouter(prefix="/admin/system", tags=["Super Admin - System"])


@router.get("/config", response_model=ApiSuccessResponse[AdminSystemConfigDTO])
async def get_system_configuration(
    super_admin: UserModel = Depends(require_super_admin),
):
    """
    Get global platform system configuration for Super Admin.
    """
    return ApiSuccessResponse(
        data=AdminSystemConfigDTO(
            environment="development",
            supported_currencies=["USD", "INR", "AED", "GBP", "EUR", "CAD", "AUD", "SGD"],
            default_timezone="UTC",
            feature_flags={
                "dynamic_pricing_enabled": True,
                "promotions_engine_enabled": True,
                "multi_home_tenancy_enabled": True,
                "optimistic_grocery_sync_enabled": True,
                "mfa_foundation_ready": True
            },
            available_system_roles=["SUPER_ADMIN", "PLATFORM_ADMIN", "SUPPORT_ADMIN", "ANALYST", "USER"],
            available_home_roles=["OWNER", "ADMIN", "MEMBER", "CHILD", "GUEST"],
            password_hashing_algorithm="Argon2id",
            mfa_enforced_for_admins=False,
            rate_limiting_enabled=True
        )
    )


@router.get("/analytics-summary", response_model=ApiSuccessResponse[AdminAnalyticsSummaryDTO])
async def get_analytics_summary(
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Analytics foundation metrics summary for Super Admin dashboard.
    """
    # Total & active users
    tot_users = (await db.execute(select(func.count(UserModel.id)))).scalar() or 0
    act_users = (await db.execute(select(func.count(UserModel.id)).where(UserModel.is_active == True))).scalar() or 0
    sus_users = tot_users - act_users

    # Total & active homes
    tot_homes = (await db.execute(select(func.count(HomeModel.id)))).scalar() or 0
    act_homes = (await db.execute(select(func.count(HomeModel.id)).where(HomeModel.status == "ACTIVE"))).scalar() or 0
    sus_homes = tot_homes - act_homes

    # Members count & average
    tot_memberships = (await db.execute(select(func.count(HomeMemberModel.id)))).scalar() or 0
    avg_members = float(tot_memberships / tot_homes) if tot_homes > 0 else 0.0

    # Subscriptions & paid seats
    act_subs = (await db.execute(select(func.count(SubscriptionModel.id)).where(SubscriptionModel.status.in_(["ACTIVE", "TRIALING"])))).scalar() or 0
    paid_seats = (await db.execute(select(func.sum(SubscriptionModel.paid_member_seats)))).scalar() or 0

    return ApiSuccessResponse(
        data=AdminAnalyticsSummaryDTO(
            total_users=tot_users,
            active_users=act_users,
            suspended_users=sus_users,
            total_homes=tot_homes,
            active_homes=act_homes,
            suspended_homes=sus_homes,
            average_members_per_home=round(avg_members, 2),
            total_active_subscriptions=act_subs,
            total_paid_member_seats=int(paid_seats),
            generated_at=datetime.now(timezone.utc)
        )
    )
