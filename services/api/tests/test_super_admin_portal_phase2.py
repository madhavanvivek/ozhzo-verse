import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api.dependencies import (
    get_current_user,
    require_admin_permission,
    require_home_permission,
    require_super_admin
)
from src.api.v1.admin_activity import list_admin_activity
from src.api.v1.admin_homes import get_home_detail, list_and_search_homes, reactivate_home, suspend_home
from src.api.v1.admin_system import get_analytics_summary, get_system_configuration
from src.api.v1.admin_users import get_user_detail, list_and_search_users, reactivate_user, suspend_user
from src.core.exceptions import PermissionDeniedException
from src.domain.permissions import (
    PLATFORM_ROLE_SUPER_ADMIN,
    PLATFORM_ROLE_USER,
    ROLE_ADMIN,
    ROLE_CHILD,
    ROLE_GUEST,
    ROLE_HOME_ADMIN,
    ROLE_MEMBER,
    ROLE_OWNER,
    has_permission,
    has_platform_permission
)
from src.infrastructure.database.models import (
    HomeMemberModel,
    HomeModel,
    SubscriptionAuditLogModel,
    SubscriptionModel,
    UserModel,
    UserProfileModel
)
from src.schemas.admin import ReactivateEntityRequest, SuspendEntityRequest


# ==============================================================================
# 1. SUPER_ADMIN Can Access Admin Dashboard & System Config
# ==============================================================================

@pytest.mark.asyncio
async def test_1_super_admin_can_access_admin_dashboard():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    # Mock DB counts for analytics summary
    mock_db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=120)),   # tot_users
        MagicMock(scalar=MagicMock(return_value=115)),   # act_users
        MagicMock(scalar=MagicMock(return_value=45)),    # tot_homes
        MagicMock(scalar=MagicMock(return_value=42)),    # act_homes
        MagicMock(scalar=MagicMock(return_value=135)),   # tot_memberships
        MagicMock(scalar=MagicMock(return_value=40)),    # act_subs
        MagicMock(scalar=MagicMock(return_value=85)),    # paid_seats
    ]

    summary_res = await get_analytics_summary(super_admin=super_admin, db=mock_db)
    assert summary_res.success is True
    assert summary_res.data.total_users == 120
    assert summary_res.data.active_users == 115
    assert summary_res.data.suspended_users == 5
    assert summary_res.data.total_homes == 45
    assert summary_res.data.active_homes == 42
    assert summary_res.data.suspended_homes == 3
    assert summary_res.data.average_members_per_home == 3.0
    assert summary_res.data.total_active_subscriptions == 40
    assert summary_res.data.total_paid_member_seats == 85

    config_res = await get_system_configuration(super_admin=super_admin)
    assert config_res.success is True
    assert "SUPER_ADMIN" in config_res.data.available_system_roles
    assert "USD" in config_res.data.supported_currencies


# ==============================================================================
# 2. SUPER_ADMIN Can List Users with Search, Filter, Pagination
# ==============================================================================

@pytest.mark.asyncio
async def test_2_super_admin_can_list_users():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    user_1 = UserModel(id=uuid4(), email="alice@example.com", is_active=True, is_super_admin=False, system_role="USER")
    user_2 = UserModel(id=uuid4(), email="bob@example.com", is_active=False, is_super_admin=False, system_role="USER")

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[
        (user_1, "Alice Smith", 2),
        (user_2, "Bob Jones", 1),
    ]))

    list_res = await list_and_search_users(query="smith", is_active=True, super_admin=super_admin, db=mock_db)
    assert list_res.success is True
    assert len(list_res.data) == 2
    assert list_res.data[0].email == "alice@example.com"
    assert list_res.data[0].display_name == "Alice Smith"
    assert list_res.data[0].homes_count == 2
    assert list_res.data[1].email == "bob@example.com"


# ==============================================================================
# 3. SUPER_ADMIN Can View User Details
# ==============================================================================

@pytest.mark.asyncio
async def test_3_super_admin_can_view_user_details():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    target_user_id = uuid4()
    target_user = UserModel(
        id=target_user_id,
        email="claire@example.com",
        phone_number="+15551234567",
        country_code="+1",
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=False,
        system_role="USER",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    target_user.profile = UserProfileModel(user_id=target_user_id, display_name="Claire D.", timezone="America/New_York")

    home_id_1 = uuid4()
    membership_1 = HomeMemberModel(home_id=home_id_1, user_id=target_user_id, role="OWNER", status="ACTIVE", created_at=datetime.now(timezone.utc))

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=target_user)),
        MagicMock(all=MagicMock(return_value=[(membership_1, "Blue Horizon Estate")])),
    ]

    detail_res = await get_user_detail(user_id=target_user_id, super_admin=super_admin, db=mock_db)
    assert detail_res.success is True
    assert detail_res.data.id == target_user_id
    assert detail_res.data.email == "claire@example.com"
    assert detail_res.data.phone_number == "+15551234567"
    assert detail_res.data.display_name == "Claire D."
    assert len(detail_res.data.memberships) == 1
    assert detail_res.data.memberships[0].home_name == "Blue Horizon Estate"
    assert detail_res.data.memberships[0].role == "OWNER"


# ==============================================================================
# 4. SUPER_ADMIN Can List Homes
# ==============================================================================

@pytest.mark.asyncio
async def test_4_super_admin_can_list_homes():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    home_1 = HomeModel(id=uuid4(), name="Palm Oasis", status="ACTIVE", currency="USD", created_by=uuid4())

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(home_1, "creator@example.com", 3, "ACTIVE")]))

    homes_res = await list_and_search_homes(query="Palm", status="ACTIVE", super_admin=super_admin, db=mock_db)
    assert homes_res.success is True
    assert len(homes_res.data) == 1
    assert homes_res.data[0].name == "Palm Oasis"
    assert homes_res.data[0].created_by_email == "creator@example.com"
    assert homes_res.data[0].members_count == 3


# ==============================================================================
# 5. SUPER_ADMIN Can View Home Details
# ==============================================================================

@pytest.mark.asyncio
async def test_5_super_admin_can_view_home_details():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    home_id = uuid4()
    creator_id = uuid4()
    home = HomeModel(id=home_id, name="Skyline Penthouse", status="ACTIVE", currency="EUR", timezone="Europe/Paris", created_by=creator_id)

    member_user_id = uuid4()
    membership = HomeMemberModel(home_id=home_id, user_id=member_user_id, role="MEMBER", status="ACTIVE", created_at=datetime.now(timezone.utc))

    mock_sub = SubscriptionModel(home_id=home_id, status="ACTIVE", paid_member_seats=5)

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(first=MagicMock(return_value=(home, "creator@paris.com", "Pierre Dupuis"))),
        MagicMock(all=MagicMock(return_value=[(membership, "member@paris.com", "+33612345678", "Jean Valjean")])),
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_sub)),
    ]

    detail_res = await get_home_detail(home_id=home_id, super_admin=super_admin, db=mock_db)
    assert detail_res.success is True
    assert detail_res.data.name == "Skyline Penthouse"
    assert detail_res.data.currency == "EUR"
    assert detail_res.data.created_by_name == "Pierre Dupuis"
    assert len(detail_res.data.members) == 1
    assert detail_res.data.members[0].email == "member@paris.com"
    assert detail_res.data.paid_seats == 5


# ==============================================================================
# 6. SUPER_ADMIN Can View Activity
# ==============================================================================

@pytest.mark.asyncio
async def test_6_super_admin_can_view_activity():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    log_id = uuid4()
    target_user_id = uuid4()

    mock_log = SubscriptionAuditLogModel(
        id=log_id,
        entity_type="USER",
        entity_id=target_user_id,
        action="SUSPEND_USER",
        performed_by=super_admin.id,
        old_values='{"is_active": true}',
        new_values='{"is_active": false}',
        reason="Terms violation",
        created_at=datetime.now(timezone.utc),
    )

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(mock_log, "superadmin@ozhzo.com")]))

    activity_res = await list_admin_activity(entity_type="USER", super_admin=super_admin, db=mock_db)
    assert activity_res.success is True
    assert len(activity_res.data) == 1
    assert activity_res.data[0].action == "SUSPEND_USER"
    assert activity_res.data[0].performed_by_email == "superadmin@ozhzo.com"
    assert activity_res.data[0].reason == "Terms violation"


# ==============================================================================
# 7-12. Household Personas Receive HTTP 403 on Super Admin Endpoints
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role_name",
    [ROLE_OWNER, ROLE_HOME_ADMIN, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST]
)
async def test_household_personas_receive_403_on_admin(role_name: str):
    user = UserModel(id=uuid4(), email=f"{role_name.lower()}@example.com", is_super_admin=False, system_role="USER")

    # 1. require_super_admin raises 403
    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert "Super Admin privileges required" in exc_info.value.detail

    # 2. require_admin_permission raises 403
    perm_dep = require_admin_permission("admin:users:view")
    with pytest.raises(HTTPException) as exc_perm:
        await perm_dep(current_user=user)
    assert exc_perm.value.status_code == 403
    assert "Super Admin privileges required" in exc_perm.value.detail


# ==============================================================================
# 13. Unauthenticated User Receives HTTP 401
# ==============================================================================

@pytest.mark.asyncio
async def test_13_unauthenticated_user_receives_401():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail


# ==============================================================================
# 14. Super Admin Cannot Suspend Themselves (HTTP 400)
# ==============================================================================

@pytest.mark.asyncio
async def test_14_super_admin_cannot_suspend_themselves():
    super_admin_id = uuid4()
    super_admin = UserModel(id=super_admin_id, email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await suspend_user(
            user_id=super_admin_id,
            payload=SuspendEntityRequest(reason="Accidental self-suspension"),
            super_admin=super_admin,
            db=mock_db,
        )
    assert exc_info.value.status_code == 400
    assert "Super Admin cannot suspend their own account" in exc_info.value.detail


# ==============================================================================
# 15. Suspended User Cannot Authenticate
# ==============================================================================

@pytest.mark.asyncio
async def test_15_suspended_user_cannot_authenticate():
    suspended_user_id = uuid4()
    suspended_user = UserModel(id=suspended_user_id, email="suspended@example.com", is_active=False)

    mock_db = AsyncMock()
    mock_db.get.return_value = suspended_user

    admin_actor = UserModel(id=uuid4(), is_super_admin=True, system_role="SUPER_ADMIN")
    res = await suspend_user(
        user_id=suspended_user_id,
        payload=SuspendEntityRequest(reason="Spam policy"),
        super_admin=admin_actor,
        db=mock_db,
    )
    assert res.success is True
    assert suspended_user.is_active is False

    # When get_current_user checks the database for active user:
    mock_db_auth = AsyncMock()
    mock_db_auth.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))  # is_active == False is excluded

    from src.core.security import create_access_token
    token = create_access_token(subject=str(suspended_user_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with pytest.raises(HTTPException) as auth_exc:
        await get_current_user(credentials=credentials, db=mock_db_auth, redis_client=mock_redis)
    assert auth_exc.value.status_code == 401
    assert "deactivated, or deleted" in auth_exc.value.detail


# ==============================================================================
# 16. Reactivation Restores User Status and Authentication
# ==============================================================================

@pytest.mark.asyncio
async def test_16_reactivation_restores_user_status():
    user_id = uuid4()
    user = UserModel(id=user_id, email="reactivated@example.com", is_active=False)

    mock_db = AsyncMock()
    mock_db.get.return_value = user

    admin_actor = UserModel(id=uuid4(), is_super_admin=True, system_role="SUPER_ADMIN")
    res = await reactivate_user(
        user_id=user_id,
        payload=ReactivateEntityRequest(reason="Appeal accepted"),
        super_admin=admin_actor,
        db=mock_db,
    )
    assert res.success is True
    assert user.is_active is True


# ==============================================================================
# 17. Sensitive Fields (password_hash, token, secret) Are Never Returned
# ==============================================================================

@pytest.mark.asyncio
async def test_17_sensitive_fields_are_never_returned():
    target_user_id = uuid4()
    target_user = UserModel(
        id=target_user_id,
        email="vault@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$secret_hash",
        is_active=True,
        is_super_admin=False,
    )
    target_user.profile = UserProfileModel(user_id=target_user_id, display_name="Vault User")

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=target_user)),
        MagicMock(all=MagicMock(return_value=[])),
    ]

    super_admin = UserModel(id=uuid4(), is_super_admin=True, system_role="SUPER_ADMIN")
    res = await get_user_detail(user_id=target_user_id, super_admin=super_admin, db=mock_db)

    dto_dict = res.data.model_dump()
    assert "password_hash" not in dto_dict
    assert "password" not in dto_dict
    assert "token" not in dto_dict
    assert "access_token" not in dto_dict
    assert "secret" not in dto_dict


# ==============================================================================
# 18. Existing Household RBAC Tests Continue Passing Untouched
# ==============================================================================

@pytest.mark.asyncio
async def test_18_existing_household_rbac_matrix_integrity():
    # Verify household matrix integrity
    assert has_permission(ROLE_OWNER, "home:edit") is True
    assert has_permission(ROLE_OWNER, "home:transfer_owner") is True
    assert has_permission(ROLE_HOME_ADMIN, "members:manage_roles") is True
    assert has_permission(ROLE_MEMBER, "inventory:view") is True
    assert has_permission(ROLE_MEMBER, "home:delete") is False
    assert has_permission(ROLE_CHILD, "tasks:complete") is True
    assert has_permission(ROLE_CHILD, "bills:pay") is False
    assert has_permission(ROLE_GUEST, "inventory:create") is False

    # Verify platform permissions matrix integrity
    assert has_platform_permission(PLATFORM_ROLE_SUPER_ADMIN, "admin:dashboard:view") is True
    assert has_platform_permission(PLATFORM_ROLE_SUPER_ADMIN, "admin:users:disable") is True
    assert has_platform_permission(PLATFORM_ROLE_USER, "admin:dashboard:view") is False
    assert has_platform_permission(PLATFORM_ROLE_USER, "admin:users:view") is False
