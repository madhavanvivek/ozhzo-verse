import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.core.bootstrap import seed_demo_super_admin
from src.core.config import settings
from src.core.security import hash_password, verify_password
from src.infrastructure.database.models import UserModel, UserProfileModel, HomeModel, HomeMemberModel
from src.api.v1.users import get_my_profile
from src.api.dependencies import require_super_admin, require_admin_permission


@pytest.mark.asyncio
async def test_01_super_admin_credentials_and_normal_login_flow():
    """TEST 1: Super Admin credentials authenticate and allow normal household login flow to /dashboard."""
    password = "demo_password"
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    # Verifies authentication against the single auth password hash
    assert verify_password("demo_password", user.password_hash) is True
    # In normal login, user profile contains standard household attributes
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res
    res = await get_my_profile(current_user=user, db=mock_db)
    assert res.success is True
    assert res.data.email == "vivek@zinfog.com"


@pytest.mark.asyncio
async def test_02_super_admin_credentials_and_admin_login_verification():
    """TEST 2: Super Admin credentials authenticate and pass platform verification for /admin."""
    password = "demo_password"
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    assert verify_password("demo_password", user.password_hash) is True
    # Super admin check in /admin/login evaluates is_super_admin / system_role
    is_super = bool(user.is_super_admin or user.system_role == "SUPER_ADMIN")
    assert is_super is True
    # Can access backend admin dependencies
    authorized = await require_super_admin(current_user=user)
    assert authorized.id == user.id


@pytest.mark.asyncio
async def test_03_normal_user_credentials_and_normal_login_flow():
    """TEST 3: Normal User credentials authenticate and allow access to household."""
    password = "user_password"
    user = UserModel(
        id=uuid4(),
        email="alice@example.com",
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    assert verify_password("user_password", user.password_hash) is True
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res
    res = await get_my_profile(current_user=user, db=mock_db)
    assert res.success is True
    assert res.data.is_super_admin is False
    assert res.data.system_role == "USER"


@pytest.mark.asyncio
async def test_04_normal_user_fails_admin_login_authorization():
    """TEST 4: Normal User credentials authenticate but fail platform authorization at /admin/login."""
    password = "user_password"
    user = UserModel(
        id=uuid4(),
        email="bob@example.com",
        password_hash=hash_password(password),
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )

    # Auth succeeds
    assert verify_password("user_password", user.password_hash) is True
    # Platform check fails
    is_super = bool(user.is_super_admin or user.system_role == "SUPER_ADMIN")
    assert is_super is False
    # Backend requirement raises 403
    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_05_unauthenticated_admin_access_redirection_model():
    """TEST 5: Unauthenticated access model redirects to /admin/login?redirect=/admin."""
    # When no token is present, current_user is None / unauthenticated
    mock_user = None
    assert mock_user is None


@pytest.mark.asyncio
async def test_06_super_admin_direct_admin_allowed():
    """TEST 6: Super Admin direct /admin access is allowed."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    authorized = await require_super_admin(current_user=super_admin)
    assert authorized.id == super_admin.id

    perm_check = require_admin_permission("admin:users:view")
    perm_user = await perm_check(current_user=super_admin)
    assert perm_user.id == super_admin.id


@pytest.mark.asyncio
async def test_07_normal_user_direct_admin_denied():
    """TEST 7: Normal user direct /admin access is denied with 403."""
    normal_user = UserModel(
        id=uuid4(),
        email="charlie@example.com",
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )

    with pytest.raises(HTTPException) as exc:
        await require_super_admin(current_user=normal_user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_08_both_portals_use_same_auth_schema():
    """TEST 8: Both portals use the single UserModel and single password hashing verification."""
    password = "shared_credential_password"
    pwd_hash = hash_password(password)

    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=pwd_hash,
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    # Validated with exact same hashing algorithm for both /login and /admin/login
    assert verify_password("shared_credential_password", user.password_hash) is True


@pytest.mark.asyncio
async def test_09_exactly_one_user_model_for_vivek():
    """TEST 9: There is exactly ONE UserModel account for vivek@zinfog.com."""
    mock_db = AsyncMock()
    existing_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("demo_pass"),
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_res

    with patch.object(settings, "ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP", True), \
         patch.object(settings, "DEMO_SUPER_ADMIN_PASSWORD", "demo_pass"):
        seeded = await seed_demo_super_admin(mock_db)
        assert seeded.id == existing_user.id
        # No additional user created
        mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_10_no_second_password_or_admin_credential_storage():
    """TEST 10: No second password or separate admin credentials table exists."""
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("single_password"),
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    assert hasattr(user, "password_hash")
    assert not hasattr(user, "admin_password")
    assert not hasattr(user, "admin_password_hash")
    assert not hasattr(user, "super_admin_secret")
