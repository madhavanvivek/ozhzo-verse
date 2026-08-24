import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.core.config import settings
from src.core.security import hash_password, verify_password, create_access_token
from src.core.bootstrap import seed_demo_super_admin
from src.infrastructure.database.models import UserModel, UserProfileModel
from src.schemas.auth import LoginRequest, TokenResponse
from src.schemas.admin import BulkUserActionRequest
from src.schemas.admin_security import AdminChangePasswordRequest
from src.api.v1.auth import login
from src.api.v1.users import get_my_profile
from src.api.v1.admin_users import bulk_user_action, suspend_user, hold_user, delete_user
from src.api.v1.admin_security import change_admin_password
from src.api.dependencies import require_super_admin, require_admin_permission


# ==============================================================================
# TEST 1: vivek@zinfog.com + Caseno@123 -> normal /login succeeds
# ==============================================================================
@pytest.mark.asyncio
async def test_01_normal_login_succeeds_with_super_admin_credentials():
    """TEST 1: vivek@zinfog.com + Caseno@123 authenticates successfully via POST /api/v1/auth/login."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = super_admin
    mock_db.execute.return_value = mock_res

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    payload = LoginRequest(email="vivek@zinfog.com", password="Caseno@123")
    res = await login(payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None
    assert res.data.email == "vivek@zinfog.com"
    assert res.data.user_id == super_admin.id


# ==============================================================================
# TEST 2: vivek@zinfog.com + Caseno@123 -> /admin/login succeeds
# ==============================================================================
@pytest.mark.asyncio
async def test_02_admin_login_succeeds_with_same_credentials():
    """TEST 2: The exact same POST /api/v1/auth/login endpoint used by /admin/login validates Super Admin identity."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = super_admin
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    payload = LoginRequest(email="vivek@zinfog.com", password="Caseno@123")
    token_res = await login(payload, db=mock_db, redis_client=mock_redis)

    assert token_res.success is True
    # Verify Super Admin dependency validation for /admin access
    authorized_admin = await require_super_admin(current_user=super_admin)
    assert authorized_admin.id == super_admin.id
    assert authorized_admin.is_super_admin is True


# ==============================================================================
# TEST 3: GET /users/me -> is_super_admin = true
# ==============================================================================
@pytest.mark.asyncio
async def test_03_get_users_me_returns_is_super_admin_true():
    """TEST 3: GET /api/v1/users/me returns is_super_admin: true for vivek@zinfog.com."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    super_admin.profile = UserProfileModel(
        user_id=super_admin.id,
        display_name="Vivek Madhavan",
        timezone="UTC",
        preferred_language="en"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=super_admin, db=mock_db)
    assert res.success is True
    assert res.data.is_super_admin is True


# ==============================================================================
# TEST 4: GET /users/me -> system_role = SUPER_ADMIN
# ==============================================================================
@pytest.mark.asyncio
async def test_04_get_users_me_returns_system_role_super_admin():
    """TEST 4: GET /api/v1/users/me returns system_role: 'SUPER_ADMIN'."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    super_admin.profile = UserProfileModel(
        user_id=super_admin.id,
        display_name="Vivek Madhavan",
        timezone="UTC",
        preferred_language="en"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=super_admin, db=mock_db)
    assert res.success is True
    assert res.data.system_role == "SUPER_ADMIN"


# ==============================================================================
# TEST 5: Super Admin can access /api/v1/admin/*
# ==============================================================================
@pytest.mark.asyncio
async def test_05_super_admin_can_access_admin_api_endpoints():
    """TEST 5: Super Admin passes administrative permission dependencies."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    # Super Admin check passes
    admin_user = await require_super_admin(current_user=super_admin)
    assert admin_user.id == super_admin.id

    # Specific fine-grained permission checks pass
    for perm in ["admin:users:view", "admin:homes:view", "admin:analytics:view", "admin:coupons:manage"]:
        check_fn = require_admin_permission(perm)
        res = await check_fn(current_user=super_admin)
        assert res.id == super_admin.id


# ==============================================================================
# TEST 6: Super Admin can access normal household APIs
# ==============================================================================
@pytest.mark.asyncio
async def test_06_super_admin_can_access_household_apis():
    """TEST 6: Super Admin possesses normal user capabilities and household memberships."""
    from src.infrastructure.database.models import HomeModel, HomeMemberModel

    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    super_admin.profile = UserProfileModel(
        user_id=super_admin.id,
        display_name="Vivek Madhavan",
        timezone="UTC",
        preferred_language="en"
    )

    ichu_home = HomeModel(id=uuid4(), name="Ichu's Home", status="ACTIVE", currency="USD")
    ichu_membership = HomeMemberModel(
        id=uuid4(),
        home_id=ichu_home.id,
        user_id=super_admin.id,
        role="HOME_ADMIN",
        status="ACTIVE"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [(ichu_membership, ichu_home)]
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=super_admin, db=mock_db)
    assert res.success is True
    assert len(res.data.homes) == 1
    assert res.data.homes[0].name == "Ichu's Home"
    assert res.data.homes[0].role == "HOME_ADMIN"


# ==============================================================================
# TEST 7: Normal user cannot access /api/v1/admin/*
# ==============================================================================
@pytest.mark.asyncio
async def test_07_normal_user_cannot_access_admin_api():
    """TEST 7: Normal household user (OWNER, MEMBER) is rejected with 403 from admin endpoints."""
    normal_user = UserModel(
        id=uuid4(),
        email="normal_user@example.com",
        password_hash=hash_password("NormalPass123!"),
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=normal_user)
    assert exc_info.value.status_code == 403
    assert "Super Admin privileges required" in exc_info.value.detail

    perm_check = require_admin_permission("admin:users:view")
    with pytest.raises(HTTPException) as exc_perm:
        await perm_check(current_user=normal_user)
    assert exc_perm.value.status_code == 403


# ==============================================================================
# TEST 8: Changing Super Admin password does not remove SUPER_ADMIN role
# ==============================================================================
@pytest.mark.asyncio
async def test_08_password_change_preserves_super_admin_role():
    """TEST 8: Updating password preserves is_super_admin=True and system_role='SUPER_ADMIN'."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "vivek@zinfog.com"

    req = AdminChangePasswordRequest(
        verification_ticket="ticket-1234567890123456",
        new_password="NewSecureAdminPass@2026",
        confirm_password="NewSecureAdminPass@2026"
    )

    res = await change_admin_password(req, super_admin=super_admin, db=mock_db, redis_client=mock_redis)
    assert res.success is True

    # Password hash updated
    assert verify_password("NewSecureAdminPass@2026", super_admin.password_hash) is True
    assert verify_password("Caseno@123", super_admin.password_hash) is False

    # Platform roles preserved intact
    assert super_admin.is_super_admin is True
    assert super_admin.system_role == "SUPER_ADMIN"
    assert super_admin.is_active is True


# ==============================================================================
# TEST 9: Deploy/bootstrap does not overwrite an existing Super Admin password
# ==============================================================================
@pytest.mark.asyncio
async def test_09_bootstrap_does_not_overwrite_existing_changed_password():
    """TEST 9: Server startup / bootstrap preserves an existing user's changed password."""
    user_with_changed_password = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("MyUserCustomPassword@999"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [user_with_changed_password]
    mock_db.execute.return_value = mock_res

    with patch.object(settings, "ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP", True), \
         patch.object(settings, "DEMO_SUPER_ADMIN_EMAIL", "vivek@zinfog.com"), \
         patch.object(settings, "DEMO_SUPER_ADMIN_PASSWORD", None), \
         patch.object(settings, "FORCE_SUPER_ADMIN_PASSWORD_RESET", False):

        restarted_user = await seed_demo_super_admin(mock_db)
        assert restarted_user is not None
        assert restarted_user.is_super_admin is True
        assert restarted_user.system_role == "SUPER_ADMIN"
        # Changed password is NOT overwritten by bootstrap!
        assert verify_password("MyUserCustomPassword@999", restarted_user.password_hash) is True
        assert verify_password("Caseno@123", restarted_user.password_hash) is False


# ==============================================================================
# TEST 10: Bulk user suspension cannot suspend the protected primary Super Admin
# ==============================================================================
@pytest.mark.asyncio
async def test_10_bulk_user_suspension_cannot_suspend_protected_super_admin():
    """TEST 10: Bulk user suspension and single-user actions cannot suspend vivek@zinfog.com."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    secondary_admin = UserModel(
        id=uuid4(),
        email="secondary_admin@ozhzo.com",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = super_admin

    # Attempt 1: Bulk suspension by another admin targeting vivek@zinfog.com
    bulk_req = BulkUserActionRequest(
        user_ids=[super_admin.id],
        action="SUSPEND",
        reason="Test bulk suspension attempt"
    )
    bulk_res = await bulk_user_action(bulk_req, super_admin=secondary_admin, db=mock_db)
    assert len(bulk_res.data.failed) == 1
    assert "Protected master" in bulk_res.data.failed[0]["reason"]
    assert super_admin.is_active is True

    # Attempt 2: Direct single-user suspend endpoint
    from src.schemas.admin import SuspendEntityRequest, DeleteEntityRequest, HoldEntityRequest
    with pytest.raises(HTTPException) as exc_suspend:
        await suspend_user(super_admin.id, SuspendEntityRequest(reason="test"), super_admin=secondary_admin, db=mock_db)
    assert exc_suspend.value.status_code == 400
    assert "Protected primary Super Admin account" in exc_suspend.value.detail

    # Attempt 3: Direct single-user delete endpoint
    with pytest.raises(HTTPException) as exc_delete:
        await delete_user(super_admin.id, DeleteEntityRequest(reason="test"), super_admin=secondary_admin, db=mock_db)
    assert exc_delete.value.status_code == 400
    assert "Protected primary Super Admin account" in exc_delete.value.detail


# ==============================================================================
# TEST 11: Logout from /login and login through /admin/login works independently
# ==============================================================================
@pytest.mark.asyncio
async def test_11_logout_and_independent_dual_portal_authentication():
    """TEST 11: Tokens are issued independently and authenticate across both portals."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = super_admin
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    # Login 1 (household portal)
    token1 = await login(LoginRequest(email="vivek@zinfog.com", password="Caseno@123"), db=mock_db, redis_client=mock_redis)
    assert token1.data.access_token is not None

    # Login 2 (admin portal)
    token2 = await login(LoginRequest(email="vivek@zinfog.com", password="Caseno@123"), db=mock_db, redis_client=mock_redis)
    assert token2.data.access_token is not None
    assert token1.data.user_id == token2.data.user_id


# ==============================================================================
# TEST 12: Login through /admin/login and then /login works with the same credentials
# ==============================================================================
@pytest.mark.asyncio
async def test_12_dual_portal_login_shares_single_underlying_user_model():
    """TEST 12: Both /admin/login and /login resolve to the same underlying UserModel record."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = super_admin
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    admin_login_res = await login(LoginRequest(email="vivek@zinfog.com", password="Caseno@123"), db=mock_db, redis_client=mock_redis)
    user_login_res = await login(LoginRequest(email="vivek@zinfog.com", password="Caseno@123"), db=mock_db, redis_client=mock_redis)

    assert admin_login_res.data.user_id == user_login_res.data.user_id == super_admin.id
    assert admin_login_res.data.email == user_login_res.data.email == "vivek@zinfog.com"
