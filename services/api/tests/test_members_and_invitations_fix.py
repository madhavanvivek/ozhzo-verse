import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.members import (
    list_home_members,
    create_invitation,
    cancel_home_invitation,
    resend_home_invitation,
    update_member_role,
    remove_home_member,
    accept_invitation,
)
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    UserModel,
    UserProfileModel,
)
from src.schemas.home import CreateInvitationRequest, UpdateMemberRoleRequest


@pytest.fixture
def mock_admin_ctx():
    user = UserModel(
        id=uuid4(),
        email="alex.rivera@ozhzo.com",
        phone_number="+919876500001",
        is_super_admin=False,
        system_role="USER",
        mobile_verified=True,
    )
    return HomeContext(
        home_id=uuid4(),
        user=user,
        role="HOME_ADMIN",
    )


@pytest.mark.asyncio
async def test_01_list_home_members_display_names(mock_admin_ctx):
    db = AsyncMock()
    member1 = HomeMemberModel(
        id=uuid4(),
        home_id=mock_admin_ctx.home_id,
        user_id=mock_admin_ctx.user.id,
        role="HOME_ADMIN",
        status="ACTIVE",
        joined_at=datetime.now(timezone.utc),
    )
    user1 = mock_admin_ctx.user
    prof1 = UserProfileModel(user_id=user1.id, display_name="Alex Rivera")

    mock_res = MagicMock()
    mock_res.all.return_value = [(member1, user1, prof1)]
    db.execute.return_value = mock_res

    res = await list_home_members(home_ctx=mock_admin_ctx, db=db)
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].display_name == "Alex Rivera"
    assert res.data[0].role == "HOME_ADMIN"
    assert res.data[0].status == "ACTIVE"


@pytest.mark.asyncio
async def test_02_create_invitation_standard_and_invite_only(mock_admin_ctx):
    db = AsyncMock()
    mock_home = HomeModel(id=mock_admin_ctx.home_id, name="Rivera Household")
    db.get.return_value = mock_home

    # 1. Standard mode
    req1 = CreateInvitationRequest(
        email="sarah@example.com",
        role="MEMBER",
        invitation_mode="STANDARD"
    )
    res1 = await create_invitation(payload=req1, home_ctx=mock_admin_ctx, db=db)
    assert res1.success is True
    assert res1.data.email == "sarah@example.com"
    assert res1.data.role == "MEMBER"
    assert res1.data.invitation_mode == "INVITE_ONLY"
    assert res1.data.home_name == "Rivera Household"
    assert len(res1.data.token) > 10

    # 2. Child role
    req2 = CreateInvitationRequest(
        phone_number="+919876543210",
        role="CHILD",
        invitation_mode="INVITE_ONLY"
    )
    res2 = await create_invitation(payload=req2, home_ctx=mock_admin_ctx, db=db)
    assert res2.success is True
    assert res2.data.role == "CHILD"
    assert res2.data.phone_number == "+919876543210"


@pytest.mark.asyncio
async def test_03_cancel_and_resend_invitation(mock_admin_ctx):
    db = AsyncMock()
    inv_id = uuid4()
    mock_inv = InvitationModel(
        id=inv_id,
        home_id=mock_admin_ctx.home_id,
        email="test.member@ozhzo.com",
        role="MEMBER",
        invitation_mode="INVITE_ONLY",
        token="old_token_123",
        status="PENDING",
        invited_by=mock_admin_ctx.user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_inv
    db.execute.return_value = mock_res
    db.get.return_value = HomeModel(id=mock_admin_ctx.home_id, name="Rivera Household")

    # Resend
    res_resend = await resend_home_invitation(invitation_id=inv_id, home_ctx=mock_admin_ctx, db=db)
    assert res_resend.success is True
    assert mock_inv.token != "old_token_123"

    # Cancel
    res_cancel = await cancel_home_invitation(invitation_id=inv_id, home_ctx=mock_admin_ctx, db=db)
    assert res_cancel.success is True
    assert mock_inv.status == "REVOKED"


@pytest.mark.asyncio
async def test_04_update_member_role_and_remove(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()
    target_member_id = uuid4()
    target_user_id = uuid4()

    mock_member = HomeMemberModel(
        id=target_member_id,
        home_id=mock_admin_ctx.home_id,
        user_id=target_user_id,
        role="MEMBER",
        status="ACTIVE",
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_member
    db.execute.return_value = mock_res

    # Change role to ADMIN
    res_role = await update_member_role(
        member_id=target_member_id,
        payload=UpdateMemberRoleRequest(role="ADMIN"),
        home_ctx=mock_admin_ctx,
        db=db,
        redis_client=mock_redis,
    )
    assert res_role.success is True
    assert mock_member.role == "ADMIN"

    # Remove member
    res_remove = await remove_home_member(
        member_id=target_member_id,
        home_ctx=mock_admin_ctx,
        db=db,
        redis_client=mock_redis,
    )
    assert res_remove.success is True
    assert mock_member.status == "REMOVED"
