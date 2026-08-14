import pytest
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
from src.infrastructure.database.models import HomeMemberModel, UserModel
from src.schemas.subscription import CreatePromotionRequest, CreateSubscriptionPlanRequest
from src.api.v1.admin_subscriptions import create_promotion, create_subscription_plan


# ==============================================================================
# 1. SUPER_ADMIN Can Access System Administration Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_1_super_admin_can_access_system_admin_endpoints():
    """1. SUPER_ADMIN (is_super_admin=True) passes require_super_admin and executes admin endpoints."""
    super_admin_user = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True)

    # Validate dependency allows super admin
    authorized_user = await require_super_admin(current_user=super_admin_user)
    assert authorized_user.id == super_admin_user.id
    assert authorized_user.is_super_admin is True

    # Validate super admin can execute administrative endpoint
    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    req = CreatePromotionRequest(
        name="Super Admin Campaign",
        code="SYS_ADMIN_PROMO",
        discount_type="PERCENTAGE",
        discount_value=50.0
    )
    res = await create_promotion(req, super_admin=super_admin_user, db=mock_db)
    assert res.success is True
    assert res.data.code == "SYS_ADMIN_PROMO"


# ==============================================================================
# 2. HOME_ADMIN Cannot Access System Administration Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_2_home_admin_cannot_access_system_admin_endpoints():
    """2. A user who is HOME_ADMIN (is_super_admin=False) is rejected from /admin/* with 403 Forbidden."""
    home_admin_user = UserModel(id=uuid4(), email="home_admin@example.com", is_super_admin=False)

    # Even though they are an ADMIN of a home, require_super_admin rejects them
    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=home_admin_user)

    assert exc_info.value.status_code == 403
    assert "Super Admin privileges required" in exc_info.value.detail


# ==============================================================================
# 3. Normal MEMBER Cannot Access System Administration Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_3_normal_member_cannot_access_system_admin_endpoints():
    """3. A normal home MEMBER (is_super_admin=False) is rejected from /admin/* with 403 Forbidden."""
    member_user = UserModel(id=uuid4(), email="member@example.com", is_super_admin=False)

    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=member_user)

    assert exc_info.value.status_code == 403
    assert "Super Admin privileges required" in exc_info.value.detail


# ==============================================================================
# 4. ADMIN of Home A Cannot Access Home B's Data
# ==============================================================================

@pytest.mark.asyncio
async def test_4_home_admin_cannot_access_other_homes():
    """4. A user who is ADMIN of Home A is rejected with 403 Forbidden when attempting to access Home B."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    user_admin_a = UserModel(id=uuid4(), email="admin_a@example.com", is_super_admin=False)
    home_a_id = uuid4()
    home_b_id = uuid4()

    # User has ACTIVE membership only in Home A
    membership_home_a = HomeMemberModel(
        home_id=home_a_id,
        user_id=user_admin_a.id,
        role=ROLE_ADMIN,
        status="ACTIVE"
    )

    # Querying Home A succeeds
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=membership_home_a))
    checker_a = require_home_permission("tasks:create")
    ctx_a = await checker_a(home_id=home_a_id, current_user=user_admin_a, db=mock_db, redis_client=mock_redis)
    assert ctx_a.home_id == home_a_id
    assert ctx_a.role == ROLE_ADMIN

    # Querying Home B returns None (no membership in Home B) -> HTTP 403 Forbidden
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    checker_b = require_home_permission("tasks:create")

    with pytest.raises(HTTPException) as exc_info:
        await checker_b(home_id=home_b_id, current_user=user_admin_a, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
    assert "not an active member of this home" in exc_info.value.detail


# ==============================================================================
# 5. Multi-Home User With Different Roles Evaluated Independently
# ==============================================================================

@pytest.mark.asyncio
async def test_5_user_belongs_to_multiple_homes_with_different_roles():
    """
    5. A single user can belong to multiple Homes with distinct roles:
       - Home 1: ADMIN (Can invite members, cannot delete home)
       - Home 2: MEMBER (Can check shopping, cannot invite members)
       - Home 3: GUEST (Can view calendar, cannot view financial bills)
    Permissions are evaluated strictly within the context of the requested home_id.
    """
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    user = UserModel(id=uuid4(), email="poly_home_user@example.com", is_super_admin=False)
    home_1_id = uuid4()
    home_2_id = uuid4()
    home_3_id = uuid4()

    membership_1 = HomeMemberModel(home_id=home_1_id, user_id=user.id, role=ROLE_ADMIN, status="ACTIVE")
    membership_2 = HomeMemberModel(home_id=home_2_id, user_id=user.id, role=ROLE_MEMBER, status="ACTIVE")
    membership_3 = HomeMemberModel(home_id=home_3_id, user_id=user.id, role=ROLE_GUEST, status="ACTIVE")

    # --- Home 1 Context (ADMIN) ---
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=membership_1))
    
    # Can invite members in Home 1
    ctx_1 = await require_home_permission("members:invite")(
        home_id=home_1_id, current_user=user, db=mock_db, redis_client=mock_redis
    )
    assert ctx_1.role == ROLE_ADMIN

    # Cannot delete Home 1 (Admin restriction)
    with pytest.raises(PermissionDeniedException):
        await require_home_permission("home:delete")(
            home_id=home_1_id, current_user=user, db=mock_db, redis_client=mock_redis
        )

    # --- Home 2 Context (MEMBER) ---
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=membership_2))
    
    # Can check shopping items in Home 2
    ctx_2 = await require_home_permission("shopping:check")(
        home_id=home_2_id, current_user=user, db=mock_db, redis_client=mock_redis
    )
    assert ctx_2.role == ROLE_MEMBER

    # Cannot invite members in Home 2 (Member restriction)
    with pytest.raises(PermissionDeniedException):
        await require_home_permission("members:invite")(
            home_id=home_2_id, current_user=user, db=mock_db, redis_client=mock_redis
        )

    # --- Home 3 Context (GUEST) ---
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=membership_3))
    
    # Can view calendar in Home 3
    ctx_3 = await require_home_permission("calendar:view")(
        home_id=home_3_id, current_user=user, db=mock_db, redis_client=mock_redis
    )
    assert ctx_3.role == ROLE_GUEST

    # Cannot view financial bills in Home 3 (Guest restriction)
    with pytest.raises(PermissionDeniedException):
        await require_home_permission("bills:view")(
            home_id=home_3_id, current_user=user, db=mock_db, redis_client=mock_redis
        )

    # --- System Level Verification ---
    # In all 3 homes, this user is NEVER a Super Admin
    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=user)
    assert exc_info.value.status_code == 403
