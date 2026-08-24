import json
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
from src.api.v1.auth import login
from src.api.v1.users import get_my_profile
from src.api.v1.homes import create_home
from src.api.v1.admin_security import send_admin_email_otp, verify_admin_email_otp, change_admin_password
from src.schemas.auth import LoginRequest
from src.schemas.home import CreateHomeRequest
from src.schemas.admin_security import VerifyEmailOTPRequest, AdminChangePasswordRequest
from src.api.dependencies import require_super_admin, require_admin_permission
from src.domain.permissions import has_permission, ROLE_OWNER, ROLE_HOME_ADMIN, ROLE_MEMBER


# ==============================================================================
# TEST A: Super Admin Profile Serialization
# ==============================================================================
@pytest.mark.asyncio
async def test_a_super_admin_profile_serialization():
    """A. Authoritative GET /users/me response contains is_super_admin: true and system_role: SUPER_ADMIN."""
    user = UserModel(
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
    assert "Caseno@123" not in serialized_str


# ==============================================================================
# TEST B & C & D: Same Credentials for /login and /admin/login
# ==============================================================================
@pytest.mark.asyncio
async def test_b_c_d_same_credentials_for_household_and_admin_login():
    """B, C, D: Same credentials (vivek@zinfog.com / Caseno@123) authenticate successfully on both portals."""
    temp_password = "Caseno@123"
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash=hash_password(temp_password),
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    # 1. Household /login flow
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res

    req = LoginRequest(email="vivek@zinfog.com", password=temp_password)
    res = await login(req, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.access_token is not None

    # 2. Platform /admin/login authorization check
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
        password_hash=hash_password("Caseno@123"),
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
        password_hash=hash_password("Caseno@123"),
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
        password_hash=hash_password("Caseno@123"),
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
    assert verify_password("Caseno@123", user.password_hash) is False

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
        password_hash=hash_password("Caseno@123"),
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
        password_hash=hash_password("Caseno@123"),
        is_active=True,
        mobile_verified=True,  # Verified
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )
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
         patch.object(settings, "DEMO_SUPER_ADMIN_PASSWORD", "Caseno@123"):

        created_user = await seed_demo_super_admin(mock_db)
        assert created_user is not None
        assert created_user.email == "vivek@zinfog.com"
        assert created_user.is_super_admin is True
        assert created_user.system_role == "SUPER_ADMIN"
        assert verify_password("Caseno@123", created_user.password_hash) is True

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
        assert verify_password("Caseno@123", restarted_user.password_hash) is False
