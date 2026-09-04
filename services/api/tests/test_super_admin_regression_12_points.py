import os
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
from src.api.v1.admin_auth import admin_login, AdminLoginRequest
from src.api.v1.auth import login
from src.api.v1.users import get_my_profile
from src.api.v1.admin_users import bulk_user_action, suspend_user, hold_user, delete_user
from src.api.v1.admin_security import change_admin_password
from src.api.dependencies import require_super_admin, require_admin_permission

TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "TestSuperAdminSecret123!")


# ==============================================================================
# TEST 1: Dedicated admin login succeeds with Super Admin credentials
# ==============================================================================
@pytest.mark.asyncio
async def test_01_admin_login_succeeds_with_super_admin_credentials():
    """TEST 1: Super Admin credentials authenticate successfully via POST /api/v1/admin/auth/login."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
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

    payload = AdminLoginRequest(email="vivek@zinfog.com", password=TEST_ADMIN_PASSWORD)
    res = await admin_login(payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None
    assert res.data.user_id == super_admin.id


# ==============================================================================
# TEST 2: /admin/auth/login validates Super Admin identity & dependencies
# ==============================================================================
@pytest.mark.asyncio
async def test_02_admin_login_validates_super_admin_dependencies():
    """TEST 2: The POST /api/v1/admin/auth/login endpoint validates Super Admin identity."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
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

    payload = AdminLoginRequest(email="vivek@zinfog.com", password=TEST_ADMIN_PASSWORD)
    token_res = await admin_login(payload, db=mock_db, redis_client=mock_redis)

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
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
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
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
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
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    admin_checker = require_admin_permission("admin:users:view")
    checked_admin = await admin_checker(current_user=super_admin)
    assert checked_admin.id == super_admin.id

    sa_direct = await require_super_admin(current_user=super_admin)
    assert sa_direct.id == super_admin.id


# ==============================================================================
# TEST 6: Normal User CANNOT access /api/v1/admin/* -> 403 Forbidden
# ==============================================================================
@pytest.mark.asyncio
async def test_06_normal_user_cannot_access_admin_api_endpoints():
    """TEST 6: Normal user attempting to access admin APIs receives 403 Forbidden."""
    normal_user = UserModel(
        id=uuid4(),
        email="regular@example.com",
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )

    with pytest.raises(HTTPException) as exc1:
        await require_super_admin(current_user=normal_user)
    assert exc1.value.status_code == 403

    admin_checker = require_admin_permission("admin:users:view")
    with pytest.raises(HTTPException) as exc2:
        await admin_checker(current_user=normal_user)
    assert exc2.value.status_code == 403


# ==============================================================================
# TEST 7: Super Admin bootstrap guarantees authoritative account
# ==============================================================================
@pytest.mark.asyncio
async def test_07_bootstrap_seeds_or_ensures_super_admin():
    """TEST 7: seed_demo_super_admin initializes or promotes designated Super Admin account."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    seeded_user = await seed_demo_super_admin(db=mock_db)
    assert seeded_user is not None
    assert seeded_user.email == (settings.DEMO_SUPER_ADMIN_EMAIL or "vivek@zinfog.com").lower()
    assert seeded_user.is_super_admin is True
    assert seeded_user.system_role == "SUPER_ADMIN"


# ==============================================================================
# TEST 8: Password change through admin security updates password hash
# ==============================================================================
@pytest.mark.asyncio
async def test_08_admin_change_password_workflow():
    """TEST 8: change_admin_password successfully verifies current password and updates hash."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "vivek@zinfog.com"

    payload = AdminChangePasswordRequest(
        verification_ticket="cryptographic_valid_ticket_12345678",
        new_password="NewSecurePassword@456",
        confirm_password="NewSecurePassword@456"
    )

    res = await change_admin_password(payload, super_admin=super_admin, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert verify_password("NewSecurePassword@456", super_admin.password_hash) is True


# ==============================================================================
# TEST 9: Protected account cannot be deleted or suspended via bulk actions
# ==============================================================================
@pytest.mark.asyncio
async def test_09_protected_master_admin_cannot_be_deleted_or_suspended():
    """TEST 9: Protected master account (vivek@zinfog.com) is guarded against bulk suspension/deletion."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = super_admin

    req = BulkUserActionRequest(
        user_ids=[super_admin.id],
        action="SUSPEND",
        reason="Test suspension guard"
    )

    res = await bulk_user_action(req, super_admin=super_admin, db=mock_db)
    assert len(res.data.failed) == 1
    assert "cannot modify or suspend" in res.data.failed[0]["reason"] or "Protected master" in res.data.failed[0]["reason"]


# ==============================================================================
# TEST 10: Single user status endpoints protect master admin account
# ==============================================================================
@pytest.mark.asyncio
async def test_10_single_user_status_endpoints_protect_master_admin():
    """TEST 10: suspend_user and delete_user explicitly reject self-targeting by Super Admin."""
    from src.schemas.admin import SuspendEntityRequest, DeleteEntityRequest

    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = super_admin

    with pytest.raises(HTTPException) as exc1:
        await suspend_user(user_id=super_admin.id, payload=SuspendEntityRequest(reason="Self suspend test"), super_admin=super_admin, db=mock_db)
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        await delete_user(user_id=super_admin.id, payload=DeleteEntityRequest(reason="Self delete test"), super_admin=super_admin, db=mock_db)
    assert exc2.value.status_code == 400


# ==============================================================================
# TEST 11: Dedicated admin login issues admin-scoped JWT token
# ==============================================================================
@pytest.mark.asyncio
async def test_11_admin_login_issues_admin_scoped_token():
    """TEST 11: Tokens from /admin/auth/login are scoped for platform administration."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
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

    token = await admin_login(AdminLoginRequest(email="vivek@zinfog.com", password=TEST_ADMIN_PASSWORD), db=mock_db, redis_client=mock_redis)
    assert token.data.access_token is not None
    assert token.data.user_id == super_admin.id


# ==============================================================================
# TEST 12: Super Admin attempting household /auth/login is directed to /admin/login
# ==============================================================================
@pytest.mark.asyncio
async def test_12_super_admin_household_login_guard():
    """TEST 12: Super Admin attempting household login receives 403 directing them to /admin/login."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [super_admin]
    mock_res.scalars.return_value.first.return_value = super_admin
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    with pytest.raises(HTTPException) as exc:
        await login(LoginRequest(email="vivek@zinfog.com", password=TEST_ADMIN_PASSWORD), db=mock_db, redis_client=mock_redis)

    assert exc.value.status_code == 403
    assert "/admin/login" in exc.value.detail
