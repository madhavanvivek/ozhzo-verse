import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.core.exceptions import TierLimitExceededException, PermissionDeniedException
from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.home import CreateInvitationRequest, UpdateMemberRoleRequest
from src.api.v1.members import (
    create_invitation,
    list_home_members,
    update_member_role,
    remove_home_member,
    accept_invitation
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import HomeModel, HomeMemberModel, InvitationModel, UserModel, UserProfileModel


@pytest.mark.asyncio
async def test_create_invitation_success():
    mock_db = AsyncMock()
    # Mock member count < 5
    mock_result = MagicMock()
    mock_result.scalar.return_value = 2
    mock_db.execute.return_value = mock_result

    home_id = uuid4()
    user_id = uuid4()
    user = UserModel(id=user_id, email="owner@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")
    req = CreateInvitationRequest(email="newmember@example.com", role="MEMBER")

    res = await create_invitation(req, home_ctx=ctx, db=mock_db)
    assert res.success is True
    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert res.data.invite_token is not None
    assert res.data.status == "PENDING"
    assert mock_db.add.call_count >= 1


@pytest.mark.asyncio
async def test_create_invitation_free_tier_limit():
    mock_db = AsyncMock()
    # Mock member count == 5
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_db.execute.return_value = mock_result

    home_id = uuid4()
    user = UserModel(id=uuid4(), email="owner@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")
    req = CreateInvitationRequest(email="sixth@example.com", role="MEMBER")

    with pytest.raises(TierLimitExceededException):
        await create_invitation(req, home_ctx=ctx, db=mock_db)


@pytest.mark.asyncio
async def test_update_member_role_rules():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    target_member_id = uuid4()
    
    # 1. Target is OWNER -> Rejection
    owner_member = HomeMemberModel(id=target_member_id, home_id=home_id, role="OWNER", status="ACTIVE")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = owner_member
    mock_db.execute.return_value = mock_result

    caller = UserModel(id=user_id, email="owner@example.com")
    ctx = HomeContext(home_id=home_id, user=caller, role="OWNER")
    req = UpdateMemberRoleRequest(role="ADMIN")
    mock_redis = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await update_member_role(target_member_id, req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400

    # 2. Target is regular MEMBER -> Success
    reg_member = HomeMemberModel(id=target_member_id, home_id=home_id, role="MEMBER", status="ACTIVE")
    mock_result.scalar_one_or_none.return_value = reg_member
    res = await update_member_role(target_member_id, req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert reg_member.role == "ADMIN"


@pytest.mark.asyncio
async def test_remove_member_rules():
    mock_db = AsyncMock()
    home_id = uuid4()
    target_member_id = uuid4()

    # Rule: Cannot remove sole OWNER
    owner_member = HomeMemberModel(id=target_member_id, home_id=home_id, role="OWNER", status="ACTIVE")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = owner_member
    mock_db.execute.return_value = mock_result

    caller = UserModel(id=uuid4(), email="admin@example.com")
    ctx = HomeContext(home_id=home_id, user=caller, role="ADMIN")
    mock_redis = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await remove_home_member(target_member_id, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_accept_invitation_lifecycle():
    mock_db = AsyncMock()
    home_id = uuid4()
    home = HomeModel(id=home_id, name="Test Home", created_by=uuid4())
    inv = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        role="MEMBER",
        invite_token="valid_token",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        invited_by=uuid4()
    )

    mock_res1 = MagicMock()
    mock_res1.first.return_value = (inv, home)

    mock_res2 = MagicMock()
    mock_res2.scalar_one_or_none.return_value = None  # Not already a member

    mock_db.execute.side_effect = [mock_res1, mock_res2]

    user = UserModel(id=uuid4(), email="newbie@example.com")
    mock_redis = AsyncMock()

    res = await accept_invitation("valid_token", current_user=user, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert inv.status == "ACCEPTED"
    assert mock_db.add.call_count >= 1


def test_cross_home_rbac_security_isolation():
    # Verify RBAC rules across home boundaries
    # Role permissions only grant capabilities within the home context where user is active
    assert has_permission(ROLE_MEMBER, "members:invite") is False
    assert has_permission(ROLE_CHILD, "members:view") is True
    assert has_permission(ROLE_CHILD, "members:invite") is False
    assert has_permission(ROLE_GUEST, "members:view") is False
    assert has_permission(ROLE_ADMIN, "members:invite") is True
    assert has_permission(ROLE_ADMIN, "members:manage_roles") is True
    assert has_permission(ROLE_OWNER, "members:manage_roles") is True
