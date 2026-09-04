import json
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from src.core.bootstrap import seed_demo_super_admin
from src.core.config import settings
from src.core.email_service import (
    EmailOTPService,
    get_email_provider,
    DevelopmentEmailProvider,
    ProductionEmailProvider,
    SMTPEmailProvider,
    ResendEmailProvider
)
from src.core.exceptions import MobileVerificationRequiredException
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from src.infrastructure.database.models import UserModel, UserProfileModel, HomeModel, HomeMemberModel, AuditLogModel
from src.api.v1.admin_auth import admin_login, AdminLoginRequest
from src.api.v1.auth import login
from src.api.v1.users import get_my_profile
from src.api.v1.homes import create_home
from src.api.v1.admin_security import send_admin_email_otp, verify_admin_email_otp, change_admin_password
from src.schemas.auth import LoginRequest
from src.schemas.home import CreateHomeRequest
from src.schemas.admin_security import VerifyEmailOTPRequest, AdminChangePasswordRequest
from src.api.dependencies import require_super_admin, require_admin_permission
from src.domain.permissions import has_permission, ROLE_OWNER, ROLE_HOME_ADMIN, ROLE_MEMBER

TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "TestSuperAdminSecret123!")


# ==============================================================================
# TEST A: Super Admin Profile Serialization
# ==============================================================================
@pytest.mark.asyncio
async def test_a_super_admin_profile_serialization():
    """A. Authoritative GET /users/me response contains is_super_admin: true and system_role: SUPER_ADMIN."""
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    profile_res = await get_my_profile(current_user=user, db=mock_db)
    assert profile_res.success is True
    assert profile_res.data.email == "vivek@zinfog.com"
    assert profile_res.data.is_super_admin is True
    assert profile_res.data.system_role == "SUPER_ADMIN"

    # Verify password hash is NEVER serialized
    serialized_str = profile_res.model_dump_json() if hasattr(profile_res, "model_dump_json") else json.dumps(profile_res.dict(), default=str)
    assert "password_hash" not in serialized_str
    assert TEST_ADMIN_PASSWORD not in serialized_str


# ==============================================================================
# TEST B & C & D: Same Credentials for /login and /admin/login
# ==============================================================================
@pytest.mark.asyncio
async def test_b_c_d_same_credentials_for_household_and_admin_login():
    """B, C, D: Same credentials authenticate successfully on both portals."""
    temp_password = TEST_ADMIN_PASSWORD
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(temp_password),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    # 1. Dedicated /admin/auth/login flow
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_res

    req = AdminLoginRequest(email="vivek@zinfog.com", password=temp_password)
    res = await admin_login(req, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.access_token is not None

    # 2. Household /auth/login directs super admin to /admin/login (403 Forbidden)
    mock_res2 = MagicMock()
    mock_res2.scalars.return_value.all.return_value = [user]
    mock_res2.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_res2
    with pytest.raises(HTTPException) as exc:
        await login(LoginRequest(email="vivek@zinfog.com", password=temp_password), db=mock_db, redis_client=mock_redis)
    assert exc.value.status_code == 403
    assert "/admin/login" in exc.value.detail

    # 3. Platform /admin/login authorization check
    assert verify_password(temp_password, user.password_hash) is True
    assert (user.is_super_admin is True or user.system_role == "SUPER_ADMIN")

    authorized_admin = await require_super_admin(current_user=user)
    assert authorized_admin.id == user.id


# ==============================================================================
# TEST E: Super Admin + Household OWNER Works in Both Scopes
# ==============================================================================
@pytest.mark.asyncio
async def test_e_super_admin_coexists_with_household_owner():
    """E. User with is_super_admin=True and household role OWNER operates in both scopes independently."""
    user_id = uuid4()
    user = UserModel(
        id=user_id,
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    # Household role OWNER capabilities
    assert has_permission(ROLE_OWNER, "home:delete") is True
    assert has_permission(ROLE_OWNER, "members:invite") is True
    assert has_permission(ROLE_OWNER, "members:remove") is True
    assert has_permission(ROLE_OWNER, "inventory:create") is True
    assert has_permission(ROLE_OWNER, "subscription:manage") is True

    # Platform role SUPER_ADMIN capabilities
    authorized = await require_super_admin(current_user=user)
    assert authorized.id == user.id

    perm_check = require_admin_permission("admin:dashboard:view")
    perm_user = await perm_check(current_user=user)
    assert perm_user.id == user.id


# ==============================================================================
# TEST F, G, H, I: Non-Admins (OWNER, MEMBER, USER) Blocked from Platform
# ==============================================================================
@pytest.mark.asyncio
async def test_f_g_h_i_non_admins_denied_platform_access():
    """F, G, H, I: Household accounts without is_super_admin=True return 403 on admin endpoints."""
    # F: Household OWNER without platform Super Admin
    owner_user = UserModel(
        id=uuid4(),
        email="owner@household.com",
        password_hash=hash_password("Pass123!"),
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )
    with pytest.raises(HTTPException) as exc_f:
        await require_super_admin(current_user=owner_user)
    assert exc_f.value.status_code == 403

    # G: Household MEMBER without platform Super Admin
    member_user = UserModel(
        id=uuid4(),
        email="member@household.com",
        password_hash=hash_password("Pass123!"),
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )
    with pytest.raises(HTTPException) as exc_g:
        await require_super_admin(current_user=member_user)
    assert exc_g.value.status_code == 403

    # H: Normal USER without Super Admin
    plain_user = UserModel(
        id=uuid4(),
        email="plain@user.com",
        password_hash=hash_password("Pass123!"),
        is_active=True,
        is_super_admin=False,
        system_role="USER"
    )
    with pytest.raises(HTTPException) as exc_h:
        await require_super_admin(current_user=plain_user)
    assert exc_h.value.status_code == 403

    # I: Fine-grained admin permission check fails with 403
    perm_check = require_admin_permission("admin:users:view")
    with pytest.raises(HTTPException) as exc_i:
        await perm_check(current_user=plain_user)
    assert exc_i.value.status_code == 403


# ==============================================================================
# TEST J: Platform Endpoints Work for Super Admin
# ==============================================================================
@pytest.mark.asyncio
async def test_j_platform_endpoints_accessible_to_super_admin():
    """J. Super Admin passes require_super_admin and require_admin_permission dependencies."""
    super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    admin_ok = await require_super_admin(current_user=super_admin)
    assert admin_ok.id == super_admin.id

    for perm in ["admin:dashboard:view", "admin:users:view", "admin:coupons:create"]:
        check = require_admin_permission(perm)
        res = await check(current_user=super_admin)
        assert res.id == super_admin.id


# ==============================================================================
# TEST K & L: Password Change Flow & Role Preservation
# ==============================================================================
@pytest.mark.asyncio
async def test_k_l_password_change_flow_preserves_super_admin():
    """K, L: Email-verified password change updates password hash without modifying platform or household roles."""
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "vivek@zinfog.com"

    req = AdminChangePasswordRequest(
        verification_ticket="valid-ticket-1234567890123456",
        new_password="NewPermanentSuperAdminPass@2026",
        confirm_password="NewPermanentSuperAdminPass@2026"
    )

    res = await change_admin_password(req, super_admin=user, db=mock_db, redis_client=mock_redis)
    assert res.success is True

    # 1. New password verifies; old temporary password fails
    assert verify_password("NewPermanentSuperAdminPass@2026", user.password_hash) is True
    assert verify_password(TEST_ADMIN_PASSWORD, user.password_hash) is False

    # 2. Super Admin flags remain completely intact
    assert user.is_super_admin is True
    assert user.system_role == "SUPER_ADMIN"
    assert user.is_active is True


# ==============================================================================
# TEST M & N: Super Admin Mobile Verification Rules for Home Creation
# ==============================================================================
@pytest.mark.asyncio
async def test_m_n_super_admin_mobile_verification_enforcement():
    """M, N: Super Admin without mobile verification cannot create a Home, but can access permitted existing Homes."""
    # M: Super Admin with mobile_verified=False cannot create Home
    unverified_super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        mobile_verified=False,  # NOT mobile verified
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    req = CreateHomeRequest(name="New Home", currency="USD", timezone="UTC")

    with pytest.raises(MobileVerificationRequiredException):
        await create_home(req, current_user=unverified_super_admin, db=mock_db, redis_client=mock_redis)

    # N: Verified Super Admin CAN create Home
    verified_super_admin = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        mobile_verified=True,  # Verified
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
    mock_homes_res = MagicMock()
    mock_homes_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_homes_res

    home_res = await create_home(req, current_user=verified_super_admin, db=mock_db, redis_client=mock_redis)
    assert home_res.success is True
    assert home_res.data.name == "New Home"


# ==============================================================================
# TEST O: Demo OTP 123456 Works Only When Explicitly Enabled
# ==============================================================================
@pytest.mark.asyncio
async def test_o_demo_otp_works_only_when_explicitly_enabled():
    """O. When DEMO_OTP_ENABLED=True, 123456 is generated and accepted."""
    service = EmailOTPService(provider=DevelopmentEmailProvider())
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with patch.object(settings, "DEMO_OTP_ENABLED", True), \
         patch.object(settings, "DEMO_OTP_CODE", "123456"):

        email, dev_code = await service.create_and_send_otp(mock_redis, "vivek@zinfog.com")
        assert dev_code == "123456"


# ==============================================================================
# TEST P: Production Mode Generates Random OTP & Does Not Expose Plaintext Code
# ==============================================================================
@pytest.mark.asyncio
async def test_p_production_mode_random_otp_security():
    """P. When DEMO_OTP_ENABLED=False, OTP is cryptographically random and not returned in API response."""
    mock_provider = AsyncMock()
    mock_provider.send_email.return_value = True
    service = EmailOTPService(provider=mock_provider)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with patch.object(settings, "DEMO_OTP_ENABLED", False), \
         patch.object(settings, "ENVIRONMENT", "production"):

        email, dev_code = await service.create_and_send_otp(mock_redis, "vivek@zinfog.com")
        assert email == "vivek@zinfog.com"
        assert dev_code is None  # Production never returns plaintext OTP

        assert mock_provider.send_email.called
        call_args = mock_provider.send_email.call_args[0]
        # Real message was constructed
        assert "Ozhzo Verse Super Admin Password Change" in call_args[1]


# ==============================================================================
# TEST Q: Bootstrap Idempotency & Password Change Preservation
# ==============================================================================
@pytest.mark.asyncio
async def test_q_bootstrap_idempotency_and_password_preservation():
    """Q. seed_demo_super_admin initializes Super Admin and does not overwrite user's changed password on redeployment."""
    mock_db = AsyncMock()

    # 1. Initial creation when account does not exist
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res_none

    with patch.object(settings, "ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP", True), \
         patch.object(settings, "DEMO_SUPER_ADMIN_EMAIL", "vivek@zinfog.com"), \
         patch.object(settings, "DEMO_SUPER_ADMIN_PASSWORD", TEST_ADMIN_PASSWORD):

        created_user = await seed_demo_super_admin(mock_db)
        assert created_user is not None
        assert created_user.email == "vivek@zinfog.com"
        assert created_user.is_super_admin is True
        assert created_user.system_role == "SUPER_ADMIN"
        assert verify_password(TEST_ADMIN_PASSWORD, created_user.password_hash) is True

    # 2. Subsequent server restart after user changed password: password must NOT be overwritten
    user_with_changed_password = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password("MyNewChangedPass@2026"),  # User changed password
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_res_existing = MagicMock()
    mock_res_existing.scalar_one_or_none.return_value = user_with_changed_password
    mock_db.execute.return_value = mock_res_existing

    with patch.object(settings, "ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP", True), \
         patch.object(settings, "DEMO_SUPER_ADMIN_EMAIL", "vivek@zinfog.com"), \
         patch.object(settings, "DEMO_SUPER_ADMIN_PASSWORD", None):

        restarted_user = await seed_demo_super_admin(mock_db)
        assert restarted_user.is_super_admin is True
        assert restarted_user.system_role == "SUPER_ADMIN"
        # User's changed password is preserved!
        assert verify_password("MyNewChangedPass@2026", restarted_user.password_hash) is True
        assert verify_password(TEST_ADMIN_PASSWORD, restarted_user.password_hash) is False


# ==============================================================================
# TEST R: GET /admin/users Includes Super Admin
# ==============================================================================
@pytest.mark.asyncio
async def test_r_admin_users_list_includes_super_admin():
    """R. GET /admin/users returns real Super Admin account with role and homes count."""
    from src.api.v1.admin_users import list_and_search_users

    super_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN",
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    # Row tuple: (UserModel, display_name, homes_count)
    mock_res.all.return_value = [(super_user, "Vivek", 2)]
    mock_db.execute.return_value = mock_res

    res = await list_and_search_users(super_admin=super_user, db=mock_db)
    assert res.success is True
    assert len(res.data) == 1
    u = res.data[0]
    assert u.email == "vivek@zinfog.com"
    assert u.is_super_admin is True
    assert u.system_role == "SUPER_ADMIN"
    assert u.display_name == "Vivek"
    assert u.homes_count == 2


# ==============================================================================
# TEST S: /admin/users Search and Role Filtering
# ==============================================================================
@pytest.mark.asyncio
async def test_s_admin_users_search_and_filters():
    """S. Searching vivek@zinfog.com and filtering by SUPER_ADMIN returns Super Admin."""
    from src.api.v1.admin_users import list_and_search_users

    super_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN",
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [(super_user, "Vivek", 1)]
    mock_db.execute.return_value = mock_res

    # 1. Search by email
    res_search = await list_and_search_users(query="vivek@zinfog.com", super_admin=super_user, db=mock_db)
    assert len(res_search.data) == 1
    assert res_search.data[0].email == "vivek@zinfog.com"

    # 2. Filter by status ACTIVE
    res_active = await list_and_search_users(is_active=True, super_admin=super_user, db=mock_db)
    assert len(res_active.data) == 1

    # 3. Filter by role SUPER_ADMIN
    res_role = await list_and_search_users(system_role="SUPER_ADMIN", super_admin=super_user, db=mock_db)
    assert len(res_role.data) == 1
    assert res_role.data[0].system_role == "SUPER_ADMIN"


# ==============================================================================
# TEST T: GET /admin/users/{id} Detail Never Exposes Secrets
# ==============================================================================
@pytest.mark.asyncio
async def test_t_admin_user_detail_never_exposes_secrets():
    """T. GET /admin/users/{id} retrieves user inspection detail without password or tokens."""
    from src.api.v1.admin_users import get_user_detail

    user_id = uuid4()
    super_user = UserModel(
        id=user_id,
        email="vivek@zinfog.com",
        password_hash=hash_password(TEST_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN",
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    # Mock user query
    mock_res_user = MagicMock()
    mock_res_user.scalar_one_or_none.return_value = super_user
    # Mock memberships query
    mock_res_members = MagicMock()
    mock_res_members.all.return_value = []

    mock_db.execute.side_effect = [mock_res_user, mock_res_members]

    res = await get_user_detail(user_id=user_id, super_admin=super_user, db=mock_db)
    assert res.success is True
    assert res.data.id == user_id
    assert res.data.email == "vivek@zinfog.com"
    assert res.data.is_super_admin is True
    assert res.data.system_role == "SUPER_ADMIN"

    # Verify no secret leakage
    detail_str = res.model_dump_json() if hasattr(res, "model_dump_json") else json.dumps(res.dict(), default=str)
    assert "password_hash" not in detail_str
    assert TEST_ADMIN_PASSWORD not in detail_str
    assert "refresh_token" not in detail_str
    assert "access_token" not in detail_str


# ==============================================================================
# TEST U: Admin Analytics Counts Real DB Users & Homes
# ==============================================================================
@pytest.mark.asyncio
async def test_u_admin_analytics_counts_real_db_records():
    """U. GET /admin/system/analytics-summary aggregates real counts directly from database."""
    from src.api.v1.admin_system import get_analytics_summary

    super_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.side_effect = [
        15,  # tot_users
        14,  # act_users
        5,   # tot_homes
        5,   # act_homes
        12,  # tot_memberships
        4,   # act_subs
        10   # paid_seats
    ]
    mock_db.execute.return_value = mock_res

    res = await get_analytics_summary(super_admin=super_user, db=mock_db)
    assert res.success is True
    assert res.data.total_users == 15
    assert res.data.active_users == 14
    assert res.data.suspended_users == 1
    assert res.data.total_homes == 5
    assert res.data.average_members_per_home == 2.4


# ==============================================================================
# TEST V: Super Admin Lists Real Homes with Creator and Member Count
# ==============================================================================
@pytest.mark.asyncio
async def test_v_super_admin_lists_real_homes():
    """V. GET /admin/homes returns authoritative Home records with creator details and member counts."""
    from src.api.v1.admin_homes import list_and_search_homes

    super_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    ichu_home = HomeModel(
        id=uuid4(),
        name="ichu's home",
        status="ACTIVE",
        currency="USD",
        timezone="UTC",
        created_by=super_user.id,
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [(ichu_home, "vivek@zinfog.com", "Vivek", 3, "ACTIVE")]
    mock_db.execute.return_value = mock_res

    res = await list_and_search_homes(query=None, status=None, limit=50, offset=0, super_admin=super_user, db=mock_db)
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].name == "ichu's home"
    assert res.data[0].created_by_email == "vivek@zinfog.com"
    assert res.data[0].created_by_name == "Vivek"
    assert res.data[0].members_count == 3
    assert res.data[0].status == "ACTIVE"


# ==============================================================================
# TEST W: Non-Super-Admins Get 403 on Admin Homes
# ==============================================================================
@pytest.mark.asyncio
async def test_w_non_super_admin_forbidden_admin_homes():
    """W. Normal USER, OWNER, HOME_ADMIN without SUPER_ADMIN role get 403 Forbidden."""
    from src.api.dependencies import require_admin_permission
    from fastapi import HTTPException

    normal_user = UserModel(
        id=uuid4(),
        email="member@example.com",
        is_super_admin=False,
        system_role="USER"
    )

    checker = require_admin_permission("admin:homes:view")
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=normal_user)

    assert exc_info.value.status_code == 403
    assert "Super Admin privileges required" in exc_info.value.detail or "privileges required" in exc_info.value.detail


# ==============================================================================
# TEST X: Admin Homes Search by Name "ichu"
# ==============================================================================
@pytest.mark.asyncio
async def test_x_admin_homes_search_by_name():
    """X. Searching query='ichu' finds 'ichu\\'s home'."""
    from src.api.v1.admin_homes import list_and_search_homes

    super_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    ichu_home = HomeModel(
        id=uuid4(),
        name="ichu's home",
        status="ACTIVE",
        currency="USD",
        timezone="UTC",
        created_by=super_user.id,
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [(ichu_home, "vivek@zinfog.com", "Vivek", 1, "TRIALING")]
    mock_db.execute.return_value = mock_res

    res = await list_and_search_homes(query="ichu", status="ACTIVE", super_admin=super_user, db=mock_db)
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].name == "ichu's home"


# ==============================================================================
# TEST Y: Admin Home Detail Never Exposes Passwords or Tokens
# ==============================================================================
@pytest.mark.asyncio
async def test_y_admin_home_detail_security():
    """Y. GET /admin/homes/{id} returns details, member list and never leaks credentials."""
    from src.api.v1.admin_homes import get_home_detail

    home_id = uuid4()
    super_user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    ichu_home = HomeModel(
        id=home_id,
        name="ichu's home",
        status="ACTIVE",
        currency="USD",
        timezone="UTC",
        created_by=super_user.id,
        created_at=datetime.now(timezone.utc)
    )

    member_user = UserModel(
        id=uuid4(),
        email="ichu@example.com",
        phone_number="+1234567890",
        is_super_admin=False,
        system_role="USER"
    )

    mock_member = HomeMemberModel(
        id=uuid4(),
        home_id=home_id,
        user_id=member_user.id,
        role="MEMBER",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()
    mock_res_home = MagicMock()
    mock_res_home.first.return_value = (ichu_home, "vivek@zinfog.com", "Vivek")

    mock_res_members = MagicMock()
    mock_res_members.all.return_value = [(mock_member, "ichu@example.com", "+1234567890", "Ichu")]

    mock_res_sub = MagicMock()
    mock_res_sub.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_res_home, mock_res_members, mock_res_sub]

    res = await get_home_detail(home_id=home_id, super_admin=super_user, db=mock_db)
    assert res.success is True
    assert res.data.id == home_id
    assert res.data.name == "ichu's home"
    assert res.data.created_by_name == "Vivek"
    assert len(res.data.members) == 1
    assert res.data.members[0].display_name == "Ichu"

    detail_str = res.model_dump_json() if hasattr(res, "model_dump_json") else json.dumps(res.dict(), default=str)
    assert "password_hash" not in detail_str
    assert "access_token" not in detail_str
    assert "refresh_token" not in detail_str

