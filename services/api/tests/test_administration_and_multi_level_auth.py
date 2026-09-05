import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.api.dependencies import require_super_admin, require_home_permission
from src.core.exceptions import PermissionDeniedException
from src.domain.permissions import (
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_CHILD,
    ROLE_GUEST,
    has_permission
)
from src.infrastructure.database.models import (
    HomeMemberModel,
    HomeModel,
    PromotionModel,
    SubscriptionAuditLogModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel,
    UserProfileModel
)
from src.schemas.admin import (
    AdminAnalyticsSummaryDTO,
    AdminSystemConfigDTO,
    ReactivateEntityRequest,
    SuspendEntityRequest
)
from src.schemas.subscription import (
    CreatePromotionRequest,
    CreateSubscriptionPriceRequest
)
from src.api.v1.admin_system import get_analytics_summary, get_system_configuration
from src.api.v1.admin_users import (
    get_user_detail,
    list_and_search_users,
    reactivate_user,
    suspend_user
)
from src.api.v1.admin_homes import (
    get_home_detail,
    list_and_search_homes,
    reactivate_home,
    suspend_home
)
from src.api.v1.admin_subscriptions import create_promotion, create_subscription_price


# ==============================================================================
# Test Point 1: SUPER_ADMIN Can Access Admin Dashboard APIs
# ==============================================================================

@pytest.mark.asyncio
async def test_1_super_admin_can_access_admin_dashboard_apis():
    """1. SUPER_ADMIN can access admin dashboard & system configuration APIs."""
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)

    # 1. System config
    config_res = await get_system_configuration(super_admin=super_admin)
    assert config_res.success is True
    assert "SUPER_ADMIN" in config_res.data.available_system_roles

    # 2. Analytics summary
    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=100)),  # total users
        MagicMock(scalar=MagicMock(return_value=90)),   # active users
        MagicMock(scalar=MagicMock(return_value=25)),   # total homes
        MagicMock(scalar=MagicMock(return_value=24)),   # active homes
        MagicMock(scalar=MagicMock(return_value=75)),   # total memberships
        MagicMock(scalar=MagicMock(return_value=24)),   # active subs
        MagicMock(scalar=MagicMock(return_value=50)),   # paid seats
    ]
    analytics_res = await get_analytics_summary(super_admin=super_admin, db=mock_db)
    assert analytics_res.success is True
    assert analytics_res.data.total_users == 100
    assert analytics_res.data.active_users == 90
    assert analytics_res.data.total_homes == 25


# ==============================================================================
# Test Point 2 & 3: HOME_ADMIN & MEMBER Cannot Access Admin APIs
# ==============================================================================

@pytest.mark.asyncio
async def test_2_and_3_home_admin_and_member_cannot_access_admin_apis():
    """2 & 3. HOME_ADMIN and normal MEMBER cannot access /admin/* APIs (HTTP 403 Forbidden)."""
    home_admin = UserModel(id=uuid4(), email="home_admin@example.com", is_super_admin=False)
    normal_member = UserModel(id=uuid4(), email="member@example.com", is_super_admin=False)

    # Home Admin rejected
    with pytest.raises(HTTPException) as exc_admin:
        await require_super_admin(current_user=home_admin)
    assert exc_admin.value.status_code == 403
    assert "Super Admin privileges required" in exc_admin.value.detail

    # Member rejected
    with pytest.raises(HTTPException) as exc_member:
        await require_super_admin(current_user=normal_member)
    assert exc_member.value.status_code == 403
    assert "Super Admin privileges required" in exc_member.value.detail


# ==============================================================================
# Test Point 4: SUPER_ADMIN Can Manage Platform Users
# ==============================================================================

@pytest.mark.asyncio
async def test_4_super_admin_can_manage_users():
    """4. SUPER_ADMIN can search, inspect, suspend, and reactivate users."""
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    target_user_id = uuid4()
    target_user = UserModel(id=target_user_id, email="target@example.com", is_active=True, is_super_admin=False)
    target_profile = UserProfileModel(user_id=target_user_id, display_name="Target User")

    mock_db = AsyncMock()

    # A. Search users
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(target_user, "Target User", 2)]))
    list_res = await list_and_search_users(query="target", super_admin=super_admin, db=mock_db)
    assert list_res.success is True
    assert len(list_res.data) == 1
    assert list_res.data[0].email == "target@example.com"

    # B. Suspend user
    mock_db.get.return_value = target_user
    suspend_res = await suspend_user(target_user_id, SuspendEntityRequest(reason="Violation"), super_admin=super_admin, db=mock_db)
    assert suspend_res.success is True
    assert target_user.is_active is False

    # C. Reactivate user
    reactivate_res = await reactivate_user(target_user_id, ReactivateEntityRequest(reason="Appealed"), super_admin=super_admin, db=mock_db)
    assert reactivate_res.success is True
    assert target_user.is_active is True


# ==============================================================================
# Test Point 5: SUPER_ADMIN Can Manage Platform Homes
# ==============================================================================

@pytest.mark.asyncio
async def test_5_super_admin_can_manage_homes():
    """5. SUPER_ADMIN can search, inspect, suspend, and reactivate Homes."""
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    target_home_id = uuid4()
    target_home = HomeModel(id=target_home_id, name="Sunset Villa", status="ACTIVE", created_by=uuid4())

    mock_db = AsyncMock()

    # A. Search homes
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(target_home, "owner@example.com", 4, "ACTIVE")]))
    list_res = await list_and_search_homes(query="Sunset", super_admin=super_admin, db=mock_db)
    assert list_res.success is True
    assert len(list_res.data) == 1
    assert list_res.data[0].name == "Sunset Villa"

    # B. Suspend home
    mock_db.get.return_value = target_home
    suspend_res = await suspend_home(target_home_id, SuspendEntityRequest(reason="Commercial dispute"), super_admin=super_admin, db=mock_db)
    assert suspend_res.success is True
    assert target_home.status == "SUSPENDED"

    # C. Reactivate home
    reactivate_res = await reactivate_home(target_home_id, ReactivateEntityRequest(reason="Resolved"), super_admin=super_admin, db=mock_db)
    assert reactivate_res.success is True
    assert target_home.status == "ACTIVE"


# ==============================================================================
# Test Point 6 & 7: SUPER_ADMIN Can Manage Pricing & Promotions
# ==============================================================================

@pytest.mark.asyncio
async def test_6_and_7_super_admin_can_manage_pricing_and_promotions():
    """6 & 7. SUPER_ADMIN can create standard prices and promotional campaigns."""
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    mock_db = AsyncMock()
    plan_id = uuid4()

    # 6. Canonical pricing creation
    mock_db.get.return_value = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME")
    mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))

    price_req = CreateSubscriptionPriceRequest(
        plan_id=plan_id,
        country="US",
        currency="USD",
        list_price=Decimal("0.00"),
        additional_member_list_price=Decimal("25.00")
    )
    price_res = await create_subscription_price(price_req, super_admin=super_admin, db=mock_db)
    assert price_res.success is True
    assert price_res.data.additional_member_list_price == Decimal("25.00")
    assert price_res.data.version == 1

    # 7. Promotion creation
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))  # no existing code
    promo_req = CreatePromotionRequest(
        name="Holiday Special 40%",
        code="HOLIDAY40",
        discount_type="PERCENTAGE",
        discount_value=Decimal("40.00"),
        maximum_redemptions=500
    )
    promo_res = await create_promotion(promo_req, super_admin=super_admin, db=mock_db)
    assert promo_res.success is True
    assert promo_res.data.code == "HOLIDAY40"
    assert promo_res.data.discount_value == Decimal("40.00")


# ==============================================================================
# Test Point 8 & 9: HOME_ADMIN Can Manage Own Home, But Cannot Manage Other Homes
# ==============================================================================

@pytest.mark.asyncio
async def test_8_and_9_home_admin_isolation():
    """8 & 9. HOME_ADMIN can manage their own home, but is rejected when accessing another Home."""
    home_admin_user = UserModel(id=uuid4(), email="admin@example.com", is_super_admin=False)
    home_a_id = uuid4()
    home_b_id = uuid4()

    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    membership_a = HomeMemberModel(home_id=home_a_id, user_id=home_admin_user.id, role=ROLE_ADMIN, status="ACTIVE")

    # Accessing Home A succeeds
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=membership_a))
    ctx = await require_home_permission("members:invite")(
        home_id=home_a_id, current_user=home_admin_user, db=mock_db, redis_client=mock_redis
    )
    assert ctx.home_id == home_a_id
    assert ctx.role == ROLE_ADMIN

    # Accessing Home B fails (HTTP 403)
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    with pytest.raises(HTTPException) as exc_info:
        await require_home_permission("members:invite")(
            home_id=home_b_id, current_user=home_admin_user, db=mock_db, redis_client=mock_redis
        )
    assert exc_info.value.status_code == 403


# ==============================================================================
# Test Point 10: HOME_ADMIN Cannot Modify Global Pricing
# ==============================================================================

@pytest.mark.asyncio
async def test_10_home_admin_cannot_modify_global_pricing():
    """10. HOME_ADMIN cannot modify global standard pricing (rejected by require_super_admin)."""
    home_admin_user = UserModel(id=uuid4(), email="admin@example.com", is_super_admin=False)

    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=home_admin_user)
    assert exc_info.value.status_code == 403


# ==============================================================================
# Test Point 11: Multi-Home Membership Permission Resolution
# ==============================================================================

@pytest.mark.asyncio
async def test_11_multi_home_membership_permission_resolution():
    """11. A user belonging to multiple homes receives correct permissions evaluated per home context."""
    user = UserModel(id=uuid4(), email="user@example.com", is_super_admin=False)
    home_1 = uuid4()
    home_2 = uuid4()

    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    m1 = HomeMemberModel(home_id=home_1, user_id=user.id, role=ROLE_ADMIN, status="ACTIVE")
    m2 = HomeMemberModel(home_id=home_2, user_id=user.id, role=ROLE_MEMBER, status="ACTIVE")

    # In Home 1: Can invite members
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=m1))
    ctx1 = await require_home_permission("members:invite")(
        home_id=home_1, current_user=user, db=mock_db, redis_client=mock_redis
    )
    assert ctx1.role == ROLE_ADMIN

    # In Home 2: Cannot invite members (Member restriction)
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=m2))
    with pytest.raises(PermissionDeniedException):
        await require_home_permission("members:invite")(
            home_id=home_2, current_user=user, db=mock_db, redis_client=mock_redis
        )


# ==============================================================================
# Test Point 12: Admin Actions Create Audit Records
# ==============================================================================

@pytest.mark.asyncio
async def test_12_admin_actions_create_audit_records():
    """12. All administrative mutations record an entry in subscription_audit_logs."""
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)
    target_user_id = uuid4()
    target_user = UserModel(id=target_user_id, email="badactor@example.com", is_active=True)

    mock_db = AsyncMock()
    mock_db.get.return_value = target_user

    await suspend_user(target_user_id, SuspendEntityRequest(reason="Terms violation"), super_admin=super_admin, db=mock_db)

    # Assert db.add was called with a SubscriptionAuditLogModel
    assert mock_db.add.called
    added_obj = mock_db.add.call_args[0][0]
    assert isinstance(added_obj, SubscriptionAuditLogModel)
    assert added_obj.entity_type == "USER"
    assert added_obj.action == "SUSPEND_USER"
    assert added_obj.performed_by == super_admin.id
    assert added_obj.reason == "Terms violation"
