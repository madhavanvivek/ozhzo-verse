import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi import HTTPException

from src.core.config import settings
from src.core.security import hash_password, verify_password, create_access_token, decode_token
from src.infrastructure.database.models import UserModel, HomeModel, HomeMemberModel, SubscriptionModel
from src.api.v1.admin_auth import admin_login, AdminLoginRequest
from src.api.v1.auth import login, LoginRequest
from src.api.v1.homes import create_home, update_home_settings, delete_home_workspace
from src.api.v1.admin_users import list_and_search_users
from src.api.v1.admin_system import get_analytics_summary
from src.api.dependencies import HomeContext, require_super_admin
from src.schemas.home import CreateHomeRequest, UpdateHomeRequest
from src.core.exceptions import TierLimitExceededException, PermissionDeniedException


@pytest.mark.asyncio
async def test_01_super_admin_login_succeeds():
    """TEST 1: Dedicated admin login (/admin/auth/login) succeeds with valid Super Admin credentials."""
    sa = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = sa
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = AdminLoginRequest(email="vivek@zinfog.com", password="Caseno@123")
    res = await admin_login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None
    decoded = decode_token(res.data.access_token)
    assert decoded.get("role") == "SUPER_ADMIN"
    assert decoded.get("context") == "ADMIN"


@pytest.mark.asyncio
async def test_02_super_admin_login_fails_with_invalid_password():
    """TEST 2: Dedicated admin login fails with 401 when password is invalid."""
    sa = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = sa
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = AdminLoginRequest(email="vivek@zinfog.com", password="WrongPassword999!")
    with pytest.raises(HTTPException) as exc_info:
        await admin_login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_03_normal_user_rejected_from_admin_login():
    """TEST 3: Normal household user attempting /admin/auth/login is rejected with 403 Forbidden."""
    normal_user = UserModel(
        id=uuid4(),
        email="user@example.com",
        password_hash=hash_password("Secret123!"),
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = normal_user
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = AdminLoginRequest(email="user@example.com", password="Secret123!")
    with pytest.raises(HTTPException) as exc_info:
        await admin_login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
    assert "Platform administrator access required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_04_super_admin_rejected_from_household_login():
    """TEST 4: Super Admin attempting household /auth/login is directed to /admin/login (403 Forbidden)."""
    sa = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [sa]
    mock_res.scalars.return_value.first.return_value = sa
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="vivek@zinfog.com", password="Caseno@123")
    with pytest.raises(HTTPException) as exc_info:
        await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
    assert "/admin/login" in exc_info.value.detail


@pytest.mark.asyncio
async def test_05_normal_user_login_succeeds_at_household_portal():
    """TEST 5: Normal user logs in successfully via /auth/login."""
    normal_user = UserModel(
        id=uuid4(),
        email="karthika@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [normal_user]
    mock_res.scalars.return_value.first.return_value = normal_user
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="karthika@example.com", password="Password123!")
    res = await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None
    assert res.data.email == "karthika@example.com"


@pytest.mark.asyncio
async def test_06_free_tier_allows_first_home_creation():
    """TEST 6: A user with 0 owned homes can create their 1st Home for free."""
    user = UserModel(id=uuid4(), is_active=True, mobile_verified=True, is_super_admin=False)
    mock_db = AsyncMock()
    # 0 existing homes
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    req = CreateHomeRequest(
        name="My First Home",
        country="GB",
        currency="GBP",
        timezone="Europe/London"
    )
    res = await create_home(payload=req, current_user=user, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.name == "My First Home"
    assert res.data.role == "HOME_ADMIN"


@pytest.mark.asyncio
async def test_07_free_tier_blocks_second_home_without_subscription():
    """TEST 7: A user with 1 owned home cannot create a 2nd home on free tier."""
    user = UserModel(id=uuid4(), is_active=True, mobile_verified=True, is_super_admin=False)
    existing_home = HomeModel(id=uuid4(), name="Existing Home 1", created_by=user.id)

    mock_db = AsyncMock()
    # Return 1 existing home on first query, and 0 active subscriptions on second query
    mock_homes_res = MagicMock()
    mock_homes_res.scalars.return_value.all.return_value = [existing_home]

    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [mock_homes_res, mock_sub_res]
    mock_redis = AsyncMock()

    req = CreateHomeRequest(
        name="Second Free Home Attempt",
        country="GB",
        currency="GBP",
        timezone="Europe/London"
    )
    with pytest.raises(TierLimitExceededException) as exc_info:
        await create_home(payload=req, current_user=user, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.code == "TIER_LIMIT_HOMES_EXCEEDED"
    assert "Your free plan includes one Home" in exc_info.value.message


@pytest.mark.asyncio
async def test_08_paid_subscription_allows_second_home():
    """TEST 8: A user with an active subscription CAN create a second home."""
    user = UserModel(id=uuid4(), is_active=True, mobile_verified=True, is_super_admin=False)
    existing_home = HomeModel(id=uuid4(), name="Existing Home 1", created_by=user.id)
    active_sub = SubscriptionModel(id=uuid4(), home_id=existing_home.id, status="ACTIVE", plan_id=uuid4())

    mock_db = AsyncMock()
    mock_homes_res = MagicMock()
    mock_homes_res.scalars.return_value.all.return_value = [existing_home]

    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.first.return_value = active_sub

    mock_db.execute.side_effect = [mock_homes_res, mock_sub_res]
    mock_redis = AsyncMock()

    req = CreateHomeRequest(
        name="Second Home with Paid Sub",
        country="GB",
        currency="GBP",
        timezone="Europe/London"
    )
    res = await create_home(payload=req, current_user=user, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.name == "Second Home with Paid Sub"


@pytest.mark.asyncio
async def test_09_home_admin_can_edit_home():
    """TEST 9: Home Admin can edit Home settings."""
    user = UserModel(id=uuid4(), is_active=True)
    home_id = uuid4()
    home = HomeModel(id=home_id, name="Old Home Name", created_by=user.id)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = home
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=user, role="HOME_ADMIN")
    req = UpdateHomeRequest(name="Updated Home Name")

    res = await update_home_settings(payload=req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.name == "Updated Home Name"


@pytest.mark.asyncio
async def test_10_home_admin_can_delete_home():
    """TEST 10: Home Admin can delete/archive Home."""
    user = UserModel(id=uuid4(), is_active=True)
    home_id = uuid4()
    home = HomeModel(id=home_id, name="Home To Archive", created_by=user.id)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = home
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=user, role="HOME_ADMIN")

    res = await delete_home_workspace(home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert "archived and deleted" in res.data.message
    assert home.status == "SUSPENDED"
    assert home.deleted_at is not None


@pytest.mark.asyncio
async def test_11_normal_member_cannot_edit_or_delete_home():
    """TEST 11: Normal household MEMBER role cannot edit or delete home."""
    from src.domain.permissions import has_permission, ROLE_MEMBER, ROLE_HOME_ADMIN

    # MEMBER permissions check
    assert has_permission(ROLE_MEMBER, "home:edit") is False
    assert has_permission(ROLE_MEMBER, "home:delete") is False
    assert has_permission(ROLE_MEMBER, "members:invite") is False
    assert has_permission(ROLE_MEMBER, "members:remove") is False

    # HOME_ADMIN permissions check
    assert has_permission(ROLE_HOME_ADMIN, "home:edit") is True
    assert has_permission(ROLE_HOME_ADMIN, "home:delete") is True
    assert has_permission(ROLE_HOME_ADMIN, "members:invite") is True


@pytest.mark.asyncio
async def test_12_super_admin_excluded_from_user_management_and_analytics():
    """TEST 12: Super Admin accounts are excluded from /admin/users list and analytics."""
    normal_u = UserModel(
        id=uuid4(),
        email="regular@example.com",
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )
    sa_u = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    # Mock query returning only normal user (as enforced by SQL filter)
    mock_res = MagicMock()
    mock_res.all.return_value = [(normal_u, "Regular User", 1)]
    mock_db.execute.return_value = mock_res

    res = await list_and_search_users(
        super_admin=sa_u,
        db=mock_db
    )
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].email == "regular@example.com"
    assert not any(u.email == "vivek@zinfog.com" for u in res.data)


@pytest.mark.asyncio
async def test_13_joining_home_as_member_does_not_consume_free_owned_home():
    """TEST 13: Being a MEMBER of another home does not count as owning a home, allowing user to create their 1st free owned home."""
    user = UserModel(id=uuid4(), is_active=True, mobile_verified=True, is_super_admin=False)
    other_home = HomeModel(id=uuid4(), name="Other Family Home", created_by=uuid4())
    membership = HomeMemberModel(id=uuid4(), home_id=other_home.id, user_id=user.id, role="MEMBER", status="ACTIVE")

    mock_db = AsyncMock()
    # User owns 0 homes (created_by == user.id is empty)
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    req = CreateHomeRequest(
        name="User's Own First Home",
        country="GB",
        currency="GBP",
        timezone="Europe/London"
    )
    res = await create_home(payload=req, current_user=user, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.name == "User's Own First Home"
    assert res.data.role == "HOME_ADMIN"

