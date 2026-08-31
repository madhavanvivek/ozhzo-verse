import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.core.security import hash_password
from src.core.otp import normalize_phone_number
from src.api.v1.auth import login
from src.api.v1.members import (
    create_invitation,
    accept_invitation,
    redeem_home_invitation_code,
    get_invitation_details,
    cancel_home_invitation
)
from src.api.dependencies import HomeContext
from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    UserModel,
    UserProfileModel
)
from src.schemas.auth import LoginRequest
from src.schemas.home import CreateInvitationRequest, RedeemInvitationRequest


@pytest.mark.asyncio
async def test_01_login_with_verified_email():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    pwd_hash = hash_password("CorrectPassword123!")

    user = UserModel(
        id=user_id,
        email="testuser@example.com",
        phone_number="+919876543210",
        password_hash=pwd_hash,
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = user
    mock_scalars.scalars.return_value.all.return_value = [user]
    mock_scalars.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_scalars

    payload = LoginRequest(login_identifier="testuser@example.com", password="CorrectPassword123!")
    res = await login(payload, db=mock_db, redis_client=mock_redis)

    assert res.data.access_token is not None
    assert res.data.user_id == user_id
    assert res.data.email == "testuser@example.com"


@pytest.mark.asyncio
async def test_02_login_with_verified_mobile():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    pwd_hash = hash_password("CorrectPassword123!")

    user = UserModel(
        id=user_id,
        email="phoneuser@example.com",
        phone_number="+919876543210",
        password_hash=pwd_hash,
        is_active=True,
        is_verified=True,
        mobile_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = user
    mock_scalars.scalars.return_value.all.return_value = [user]
    mock_scalars.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_scalars

    # Login with mobile number directly
    payload = LoginRequest(login_identifier="+919876543210", password="CorrectPassword123!")
    res = await login(payload, db=mock_db, redis_client=mock_redis)

    assert res.data.access_token is not None
    assert res.data.user_id == user_id


@pytest.mark.asyncio
async def test_03_login_with_uppercase_and_spaced_email():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    pwd_hash = hash_password("CorrectPassword123!")

    user = UserModel(
        id=user_id,
        email="caseuser@example.com",
        password_hash=pwd_hash,
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = user
    mock_scalars.scalars.return_value.all.return_value = [user]
    mock_scalars.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_scalars

    payload = LoginRequest(login_identifier="   CaseUser@EXAMPLE.COM   ", password="CorrectPassword123!")
    res = await login(payload, db=mock_db, redis_client=mock_redis)

    assert res.data.access_token is not None
    assert res.data.user_id == user_id


@pytest.mark.asyncio
async def test_04_login_with_mobile_formatting_variations():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    pwd_hash = hash_password("CorrectPassword123!")

    user = UserModel(
        id=user_id,
        email="variations@example.com",
        phone_number="+919876543210",
        password_hash=pwd_hash,
        is_active=True,
        mobile_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = user
    mock_scalars.scalars.return_value.all.return_value = [user]
    mock_scalars.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_scalars

    test_inputs = [
        "9876543210",
        "+91 98765 43210",
        "09876543210",
        "91-9876543210",
        "+91-9876543210",
        "00919876543210"
    ]

    for raw_phone in test_inputs:
        payload = LoginRequest(login_identifier=raw_phone, password="CorrectPassword123!")
        res = await login(payload, db=mock_db, redis_client=mock_redis)
        assert res.data.user_id == user_id


@pytest.mark.asyncio
async def test_05_login_with_unverified_mobile_rejected():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    pwd_hash = hash_password("CorrectPassword123!")

    user = UserModel(
        id=user_id,
        email="unverifiedphone@example.com",
        phone_number="+919876543210",
        password_hash=pwd_hash,
        is_active=True,
        mobile_verified=False,  # Unverified!
        is_super_admin=False,
        system_role="USER"
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = user
    mock_scalars.scalars.return_value.all.return_value = [user]
    mock_scalars.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_scalars

    payload = LoginRequest(login_identifier="+919876543210", password="CorrectPassword123!")
    with pytest.raises(HTTPException) as exc_info:
        await login(payload, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "verify your mobile number" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_06_super_admin_rejected_from_normal_login():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    pwd_hash = hash_password("SuperAdminPass123!")

    super_admin_user = UserModel(
        id=uuid4(),
        email="superadmin@ozhzo.com",
        password_hash=pwd_hash,
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = super_admin_user
    mock_scalars.scalars.return_value.all.return_value = [super_admin_user]
    mock_scalars.scalars.return_value.first.return_value = super_admin_user
    mock_db.execute.return_value = mock_scalars

    payload = LoginRequest(login_identifier="superadmin@ozhzo.com", password="SuperAdminPass123!")
    with pytest.raises(HTTPException) as exc_info:
        await login(payload, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "/admin/login" in exc_info.value.detail


@pytest.mark.asyncio
async def test_07_personal_invitation_matching_verified_mobile():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    invitee_id = uuid4()

    # Invitee has verified mobile +919876543210
    invitee = UserModel(
        id=invitee_id,
        email="recipient@example.com",
        phone_number="+919876543210",
        mobile_verified=True,
        is_active=True
    )
    invitee.profile = UserProfileModel(user_id=invitee_id, display_name="Invited Family Member")

    home = HomeModel(id=home_id, name="Family Villa", status="ACTIVE")

    # Invitation issued to "9876543210"
    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        phone_number="+919876543210",
        role="MEMBER",
        token="personal-invite-tok-123",
        invitation_code="OZ-AB12CD",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=5)
    )

    # Mock queries:
    # 1. Fetch invitation
    inv_mock = MagicMock()
    inv_mock.first.return_value = (invitation, home)

    # 2. Check duplicate membership -> None
    mem_mock = MagicMock()
    mem_mock.scalar_one_or_none.return_value = None

    # 3. Check seat limit -> 2 members
    count_mock = MagicMock()
    count_mock.scalar.return_value = 2

    # 4. Subscription check
    sub_mock = MagicMock()
    sub_mock.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [inv_mock, mem_mock, MagicMock(), count_mock, sub_mock]

    res = await accept_invitation("personal-invite-tok-123", current_user=invitee, db=mock_db, redis_client=mock_redis)

    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert invitation.status == "ACCEPTED"
    assert invitation.accepted_by == invitee_id


@pytest.mark.asyncio
async def test_08_personal_invitation_wrong_mobile_rejected():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    wrong_user_id = uuid4()

    # Wrong user has different mobile number
    wrong_user = UserModel(
        id=wrong_user_id,
        email="wrong@example.com",
        phone_number="+919999999999",
        mobile_verified=True,
        is_active=True
    )
    home = HomeModel(id=home_id, name="Family Villa", status="ACTIVE")

    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        phone_number="+919876543210",
        role="MEMBER",
        token="target-invite-tok",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=5)
    )

    inv_mock = MagicMock()
    inv_mock.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("target-invite-tok", current_user=wrong_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "different mobile number" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_09_redeem_invitation_code_alias():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(
        id=user_id,
        email="code_user@example.com",
        is_active=True
    )
    home = HomeModel(id=home_id, name="Sunny Retreat", status="ACTIVE")

    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        phone_number=None,
        email=None,
        role="MEMBER",
        token="tok-redeem-1",
        invitation_code="OZ-E8TNUT",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=5)
    )

    inv_mock = MagicMock()
    inv_mock.first.return_value = (invitation, home)
    mem_mock = MagicMock()
    mem_mock.scalar_one_or_none.return_value = None
    count_mock = MagicMock()
    count_mock.scalar.return_value = 1
    sub_mock = MagicMock()
    sub_mock.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [inv_mock, mem_mock, MagicMock(), count_mock, sub_mock]

    payload = RedeemInvitationRequest(invitation_code="OZ-E8TNUT")
    res = await redeem_home_invitation_code(payload, current_user=user, db=mock_db, redis_client=mock_redis)

    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert invitation.status == "ACCEPTED"
