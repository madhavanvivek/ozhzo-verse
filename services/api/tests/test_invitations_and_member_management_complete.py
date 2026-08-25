import pytest
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.members import (
    generate_invitation_code,
    check_home_member_seat_limit,
    create_invitation,
    list_home_members,
    list_home_invitations,
    cancel_home_invitation,
    resend_home_invitation,
    get_invitation_details,
    accept_invitation,
    redeem_home_invitation_code,
    decline_invitation,
    update_member_role,
    remove_home_member,
)
from src.api.v1.homes import (
    update_home_settings,
    delete_home_workspace,
)
from src.api.v1.admin_homes import get_home_detail
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
    UserProfileModel,
    NotificationModel,
)
from src.schemas.home import (
    CreateInvitationRequest,
    RedeemInvitationRequest,
    UpdateMemberRoleRequest,
    UpdateHomeRequest,
)


@pytest.fixture
def mock_owner_ctx():
    user = UserModel(
        id=uuid4(),
        email="owner.test@ozhzo.com",
        phone_number="+919876500001",
        is_super_admin=False,
        system_role="USER",
        mobile_verified=True,
    )
    return HomeContext(
        home_id=uuid4(),
        user=user,
        role="OWNER",
    )


@pytest.fixture
def mock_admin_ctx(mock_owner_ctx):
    user = UserModel(
        id=uuid4(),
        email="admin.test@ozhzo.com",
        phone_number="+919876500002",
        is_super_admin=False,
        system_role="USER",
        mobile_verified=True,
    )
    return HomeContext(
        home_id=mock_owner_ctx.home_id,
        user=user,
        role="HOME_ADMIN",
    )


@pytest.fixture
def mock_member_ctx(mock_owner_ctx):
    user = UserModel(
        id=uuid4(),
        email="member.test@ozhzo.com",
        phone_number="+919876500003",
        is_super_admin=False,
        system_role="USER",
        mobile_verified=True,
    )
    return HomeContext(
        home_id=mock_owner_ctx.home_id,
        user=user,
        role="MEMBER",
    )


def test_01_invitation_code_format():
    code = generate_invitation_code()
    assert code.startswith("OZ-")
    assert len(code) == 9
    suffix = code[3:]
    assert suffix.isalnum()
    assert suffix.isupper()


@pytest.mark.asyncio
async def test_02_home_admin_creates_invitation(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()

    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 2
    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = None
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = None

    db.execute.side_effect = [
        mock_count_res,
        mock_sub_res,
        mock_user_res,
        mock_user_res,
    ]

    mock_home = HomeModel(id=mock_admin_ctx.home_id, name="Sunset Villa", deleted_at=None)
    db.get.return_value = mock_home

    req = CreateInvitationRequest(
        email="invited.family@ozhzo.com",
        role="MEMBER",
        invitation_mode="INVITE_ONLY"
    )

    res = await create_invitation(payload=req, home_ctx=mock_admin_ctx, db=db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.home_id == mock_admin_ctx.home_id
    assert res.data.home_name == "Sunset Villa"
    assert res.data.email == "invited.family@ozhzo.com"
    assert res.data.role == "MEMBER"
    assert res.data.status == "PENDING"
    assert res.data.token is not None
    assert res.data.invitation_code is not None
    assert res.data.invitation_code.startswith("OZ-")
    assert res.data.invite_url == f"/invite/{res.data.token}"
    assert db.add.call_count >= 1


@pytest.mark.asyncio
async def test_03_existing_ozhzo_user_receives_in_app_notification(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()

    existing_user_id = uuid4()
    existing_user = UserModel(id=existing_user_id, email="existing.user@ozhzo.com", is_active=True, deleted_at=None)

    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 2
    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = None
    mock_mem_res = MagicMock()
    mock_mem_res.scalar_one_or_none.return_value = None
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = existing_user

    db.execute.side_effect = [
        mock_count_res,
        mock_sub_res,
        mock_mem_res,
        mock_user_res,
    ]

    mock_home = HomeModel(id=mock_admin_ctx.home_id, name="Rivera Household", deleted_at=None)
    db.get.return_value = mock_home

    req = CreateInvitationRequest(
        email="existing.user@ozhzo.com",
        role="MEMBER"
    )

    with patch("src.services.notification_service.notification_service.dispatch", new_callable=AsyncMock) as mock_dispatch:
        res = await create_invitation(payload=req, home_ctx=mock_admin_ctx, db=db, redis_client=mock_redis)
        assert res.success is True
        mock_dispatch.assert_called_once()
        call_kwargs = mock_dispatch.call_args.kwargs
        assert call_kwargs["user_id"] == existing_user_id
        assert call_kwargs["type"] == "HOME_INVITATION"
        assert "Rivera Household" in call_kwargs["title"]


@pytest.mark.asyncio
async def test_04_list_pending_invitations_with_codes(mock_admin_ctx):
    db = AsyncMock()
    inv1 = InvitationModel(
        id=uuid4(),
        home_id=mock_admin_ctx.home_id,
        email="guest1@ozhzo.com",
        role="MEMBER",
        token="tok_12345",
        invitation_code="OZ-TEST01",
        status="PENDING",
        invited_by=mock_admin_ctx.user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.all.return_value = [(inv1, "Rivera Household", "admin@ozhzo.com", "Admin Alex")]
    db.execute.return_value = mock_res

    res = await list_home_invitations(home_ctx=mock_admin_ctx, db=db)
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].email == "guest1@ozhzo.com"
    assert res.data[0].invitation_code == "OZ-TEST01"
    assert res.data[0].token == "tok_12345"
    assert res.data[0].invite_url == "/invite/tok_12345"


@pytest.mark.asyncio
async def test_05_public_invitation_lookup_by_token_and_code():
    db = AsyncMock()
    inv = InvitationModel(
        id=uuid4(),
        home_id=uuid4(),
        email="someone@example.com",
        role="MEMBER",
        token="valid_token_xyz",
        invitation_code="OZ-CODE99",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        created_at=datetime.now(timezone.utc),
    )
    home = HomeModel(id=inv.home_id, name="Skyline Manor")
    inviter = UserModel(id=uuid4(), email="inviter@ozhzo.com")
    profile = UserProfileModel(user_id=inviter.id, display_name="Elena Vance")

    mock_res = MagicMock()
    mock_res.first.return_value = (inv, home, inviter, profile)
    db.execute.return_value = mock_res

    res = await get_invitation_details(token_or_code="valid_token_xyz", credentials=None, db=db)
    assert res.success is True
    assert res.data.home_name == "Skyline Manor"
    assert res.data.invited_by_name == "Elena Vance"
    assert res.data.role == "MEMBER"
    assert res.data.invitation_code == "OZ-CODE99"
    assert res.data.is_expired is False


@pytest.mark.asyncio
async def test_06_accept_invitation_via_link_token():
    db = AsyncMock()
    mock_redis = AsyncMock()
    joining_user = UserModel(
        id=uuid4(),
        email="newuser@ozhzo.com",
        is_active=True,
        mobile_verified=True,
    )
    inv_id = uuid4()
    home_id = uuid4()
    inv = InvitationModel(
        id=inv_id,
        home_id=home_id,
        email="newuser@ozhzo.com",
        role="MEMBER",
        token="tok_abc123",
        invitation_code="OZ-JOIN01",
        status="PENDING",
        invited_by=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
    )
    home = HomeModel(id=home_id, name="Highland Retreat", deleted_at=None, status="ACTIVE")

    mock_inv_res = MagicMock()
    mock_inv_res.first.return_value = (inv, home)
    mock_mem_res = MagicMock()
    mock_mem_res.scalar_one_or_none.return_value = None
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 2
    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = None
    mock_prof_res = MagicMock()
    mock_prof_res.scalar_one_or_none.return_value = None

    db.execute.side_effect = [
        mock_inv_res,
        mock_mem_res,
        mock_count_res,
        mock_sub_res,
        mock_prof_res,
    ]

    res = await accept_invitation(token_or_code="tok_abc123", current_user=joining_user, db=db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.home_id == home_id
    assert res.data.home_name == "Highland Retreat"
    assert res.data.role == "MEMBER"
    assert inv.status == "ACCEPTED"
    assert inv.accepted_by == joining_user.id
    assert inv.accepted_at is not None


@pytest.mark.asyncio
async def test_07_redeem_invitation_via_code():
    db = AsyncMock()
    mock_redis = AsyncMock()
    joining_user = UserModel(
        id=uuid4(),
        email="codeuser@ozhzo.com",
        is_active=True,
        mobile_verified=True,
    )
    home_id = uuid4()
    inv = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        email="codeuser@ozhzo.com",
        role="HOME_ADMIN",
        token="tok_secret_code",
        invitation_code="OZ-MANUAL",
        status="PENDING",
        invited_by=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
    )
    home = HomeModel(id=home_id, name="Sunny Grove", deleted_at=None, status="ACTIVE")

    db.execute.side_effect = [
        MagicMock(first=MagicMock(return_value=(inv, home))),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar=MagicMock(return_value=1)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]

    payload = RedeemInvitationRequest(invitation_code="OZ-MANUAL")
    res = await redeem_home_invitation_code(payload=payload, current_user=joining_user, db=db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.home_name == "Sunny Grove"
    assert res.data.role == "HOME_ADMIN"
    assert inv.status == "ACCEPTED"


@pytest.mark.asyncio
async def test_08_reused_invitation_code_rejected():
    db = AsyncMock()
    mock_redis = AsyncMock()
    user = UserModel(id=uuid4(), email="user@ozhzo.com", is_active=True)
    inv = InvitationModel(
        id=uuid4(),
        home_id=uuid4(),
        token="tok_done",
        invitation_code="OZ-REUSED",
        status="ACCEPTED",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    home = HomeModel(id=inv.home_id, name="Test Home", deleted_at=None, status="ACTIVE")

    db.execute.return_value = MagicMock(first=MagicMock(return_value=(inv, home)))

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("OZ-REUSED", current_user=user, db=db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "already been accepted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_09_expired_invitation_rejected():
    db = AsyncMock()
    mock_redis = AsyncMock()
    user = UserModel(id=uuid4(), email="user@ozhzo.com", is_active=True)
    inv = InvitationModel(
        id=uuid4(),
        home_id=uuid4(),
        token="tok_expired",
        invitation_code="OZ-EXPIRE",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    home = HomeModel(id=inv.home_id, name="Test Home", deleted_at=None, status="ACTIVE")

    db.execute.return_value = MagicMock(first=MagicMock(return_value=(inv, home)))

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("OZ-EXPIRE", current_user=user, db=db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_10_revoked_invitation_rejected():
    db = AsyncMock()
    mock_redis = AsyncMock()
    user = UserModel(id=uuid4(), email="user@ozhzo.com", is_active=True)
    inv = InvitationModel(
        id=uuid4(),
        home_id=uuid4(),
        token="tok_revoked",
        invitation_code="OZ-REVOKD",
        status="REVOKED",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    home = HomeModel(id=inv.home_id, name="Test Home", deleted_at=None, status="ACTIVE")

    db.execute.return_value = MagicMock(first=MagicMock(return_value=(inv, home)))

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("OZ-REVOKD", current_user=user, db=db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "revoked or cancelled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_11_already_member_duplicate_prevented():
    db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    user = UserModel(id=user_id, email="existing@ozhzo.com", is_active=True)
    home_id = uuid4()
    inv = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        token="tok_active",
        invitation_code="OZ-ACTIVE",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    home = HomeModel(id=home_id, name="Test Home", deleted_at=None, status="ACTIVE")
    existing_mem = HomeMemberModel(home_id=home_id, user_id=user_id, status="ACTIVE", role="MEMBER")

    db.execute.side_effect = [
        MagicMock(first=MagicMock(return_value=(inv, home))),
        MagicMock(scalar_one_or_none=MagicMock(return_value=existing_mem)),
    ]

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("OZ-ACTIVE", current_user=user, db=db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "already a member" in exc_info.value.detail


@pytest.mark.asyncio
async def test_12_seat_limit_exceeded_rejects_invitation_and_join():
    db = AsyncMock()
    home_id = uuid4()

    db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=5)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]

    with pytest.raises(HTTPException) as exc_info:
        await check_home_member_seat_limit(home_id=home_id, db=db)
    assert exc_info.value.status_code == 400
    assert "Your Home subscription does not have an available member seat." in exc_info.value.detail


@pytest.mark.asyncio
async def test_13_home_admin_can_update_member_role(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()
    target_id = uuid4()
    target_member = HomeMemberModel(id=target_id, home_id=mock_admin_ctx.home_id, user_id=uuid4(), role="MEMBER", status="ACTIVE")

    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=target_member))

    req = UpdateMemberRoleRequest(role="ADMIN")
    res = await update_member_role(target_id, req, home_ctx=mock_admin_ctx, db=db, redis_client=mock_redis)
    assert res.success is True
    assert target_member.role == "ADMIN"


@pytest.mark.asyncio
async def test_14_home_admin_can_remove_member(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()
    target_id = uuid4()
    target_member = HomeMemberModel(id=target_id, home_id=mock_admin_ctx.home_id, user_id=uuid4(), role="MEMBER", status="ACTIVE")

    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=target_member))

    res = await remove_home_member(target_id, home_ctx=mock_admin_ctx, db=db, redis_client=mock_redis)
    assert res.success is True
    assert target_member.status == "REMOVED"


@pytest.mark.asyncio
async def test_15_home_admin_can_edit_home_settings(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()
    home = HomeModel(id=mock_admin_ctx.home_id, name="Old Villa Name", currency="USD", timezone="UTC", deleted_at=None)

    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=home))

    req = UpdateHomeRequest(name="Updated Villa Name", currency="EUR", timezone="Europe/Paris")
    res = await update_home_settings(payload=req, home_ctx=mock_admin_ctx, db=db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.name == "Updated Villa Name"
    assert home.name == "Updated Villa Name"
    assert home.currency == "EUR"
    assert home.timezone == "Europe/Paris"


@pytest.mark.asyncio
async def test_16_home_admin_can_delete_archive_home(mock_admin_ctx):
    db = AsyncMock()
    mock_redis = AsyncMock()
    home = HomeModel(id=mock_admin_ctx.home_id, name="Deletable Home", status="ACTIVE", deleted_at=None)

    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=home))

    res = await delete_home_workspace(home_ctx=mock_admin_ctx, db=db, redis_client=mock_redis)
    assert res.success is True
    assert home.deleted_at is not None
    assert home.status == "SUSPENDED"


@pytest.mark.asyncio
async def test_17_super_admin_inspects_home_invitations():
    db = AsyncMock()
    super_admin = UserModel(id=uuid4(), email="super@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    home_id = uuid4()
    home = HomeModel(id=home_id, name="Grand Estate", status="ACTIVE", deleted_at=None)

    mock_home_res = MagicMock()
    mock_home_res.first.return_value = (home, "creator@ozhzo.com", "Creator Name")

    mock_member = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=uuid4(), role="HOME_ADMIN", status="ACTIVE", created_at=datetime.now(timezone.utc))
    mock_mem_res = MagicMock()
    mock_mem_res.all.return_value = [(mock_member, "member@ozhzo.com", "+919876500000", "Member User")]

    mock_inv = InvitationModel(id=uuid4(), home_id=home_id, email="invitee@ozhzo.com", role="MEMBER", invitation_code="OZ-SUPER", status="PENDING", invited_by=super_admin.id, expires_at=datetime.now(timezone.utc) + timedelta(days=5), created_at=datetime.now(timezone.utc))
    mock_inv_res = MagicMock()
    mock_inv_res.all.return_value = [(mock_inv, "super@ozhzo.com")]

    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = None

    db.execute.side_effect = [
        mock_home_res,
        mock_mem_res,
        mock_sub_res,
        mock_inv_res,
    ]

    res = await get_home_detail(home_id=home_id, super_admin=super_admin, db=db)
    assert res.success is True
    assert res.data.name == "Grand Estate"
    assert len(res.data.members) == 1
    assert len(res.data.invitations) == 1
    assert res.data.invitations[0].email == "invitee@ozhzo.com"
    assert res.data.invitations[0].invitation_code == "OZ-SUPER"
