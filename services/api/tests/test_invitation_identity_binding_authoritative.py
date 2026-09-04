import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.api.v1.members import (
    accept_invitation,
    redeem_home_invitation_code,
    get_invitation_details,
    create_invitation,
    generate_invitation_code
)
from src.core.otp import normalize_phone_number
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    UserModel,
    UserProfileModel
)
from src.schemas.home import CreateInvitationRequest, RedeemInvitationRequest
from src.api.dependencies import HomeContext


@pytest.mark.asyncio
async def test_mobile_invitation_wrong_user_rejected_and_rightful_user_accepted():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    inviter_id = uuid4()
    rightful_id = uuid4()
    wrong_id = uuid4()

    home = HomeModel(id=home_id, name="Sandhya House", status="ACTIVE", deleted_at=None)

    # Invitation issued to +15551234567
    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        invited_by=inviter_id,
        phone_number="+15551234567",
        email=None,
        role="MEMBER",
        invitation_mode="STANDARD",
        token="token-sandhya-1",
        invitation_code="OZ-FE9EDU",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # 1. Wrong user with phone +19998887777 (Vyshak)
    wrong_user = UserModel(
        id=wrong_id,
        email="vyshak@example.com",
        phone_number="+19998887777",
        mobile_verified=True,
        is_verified=True,
        is_active=True
    )

    inv_mock_wrong = MagicMock()
    inv_mock_wrong.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock_wrong

    # Direct API accept link token -> 403
    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("token-sandhya-1", current_user=wrong_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "different mobile number" in exc_info.value.detail.lower()
    assert invitation.status == "PENDING"
    assert invitation.accepted_by is None

    # Direct API redeem code -> 403
    inv_mock_wrong.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock_wrong
    with pytest.raises(HTTPException) as exc_info:
        payload = RedeemInvitationRequest(invitation_code="OZ-FE9EDU")
        await redeem_home_invitation_code(payload, current_user=wrong_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "different mobile number" in exc_info.value.detail.lower()
    assert invitation.status == "PENDING"

    # 2. Rightful user with matching verified phone +15551234567
    rightful_user = UserModel(
        id=rightful_id,
        email="rightful@sandhya.com",
        phone_number="+15551234567",
        mobile_verified=True,
        is_verified=True,
        is_active=True
    )

    inv_mock_right = MagicMock()
    inv_mock_right.first.return_value = (invitation, home)
    mem_mock = MagicMock()
    mem_mock.scalar_one_or_none.return_value = None
    count_mock = MagicMock()
    count_mock.scalar.return_value = 1
    sub_mock = MagicMock()
    sub_mock.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [inv_mock_right, mem_mock, MagicMock(), count_mock, sub_mock]

    res = await accept_invitation("token-sandhya-1", current_user=rightful_user, db=mock_db, redis_client=mock_redis)
    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert invitation.status == "ACCEPTED"
    assert invitation.accepted_by == rightful_id


@pytest.mark.asyncio
async def test_email_invitation_identity_binding():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    inviter_id = uuid4()
    rightful_id = uuid4()
    wrong_id = uuid4()

    home = HomeModel(id=home_id, name="Email House", status="ACTIVE", deleted_at=None)

    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        invited_by=inviter_id,
        phone_number=None,
        email="invited@family.com",
        role="MEMBER",
        invitation_mode="STANDARD",
        token="token-email-1",
        invitation_code="OZ-EML111",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # 1. User with no email
    no_email_user = UserModel(
        id=wrong_id,
        email=None,
        phone_number="+18881112222",
        mobile_verified=True,
        is_active=True
    )
    inv_mock = MagicMock()
    inv_mock.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("token-email-1", current_user=no_email_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "different email address" in exc_info.value.detail.lower()

    # 2. User with different email
    diff_email_user = UserModel(
        id=wrong_id,
        email="unrelated@other.com",
        phone_number="+18881112222",
        mobile_verified=True,
        is_verified=True,
        is_active=True
    )
    inv_mock.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("token-email-1", current_user=diff_email_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "different email address" in exc_info.value.detail.lower()

    # 3. User with unverified matching email
    unverified_email_user = UserModel(
        id=wrong_id,
        email="invited@family.com",
        phone_number="+18881112222",
        mobile_verified=True,
        is_verified=False,
        is_active=True
    )
    inv_mock.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("token-email-1", current_user=unverified_email_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "verify your email address" in exc_info.value.detail.lower()

    # 4. User with matching verified email -> 200 OK
    rightful_user = UserModel(
        id=rightful_id,
        email="Invited@Family.com",  # Case insensitive test
        phone_number="+18881112222",
        mobile_verified=True,
        is_verified=True,
        is_active=True
    )
    inv_mock_right = MagicMock()
    inv_mock_right.first.return_value = (invitation, home)
    mem_mock = MagicMock()
    mem_mock.scalar_one_or_none.return_value = None
    count_mock = MagicMock()
    count_mock.scalar.return_value = 1
    sub_mock = MagicMock()
    sub_mock.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [inv_mock_right, mem_mock, MagicMock(), count_mock, sub_mock]

    res = await accept_invitation("token-email-1", current_user=rightful_user, db=mock_db, redis_client=mock_redis)
    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert invitation.status == "ACCEPTED"
    assert invitation.accepted_by == rightful_id


@pytest.mark.asyncio
async def test_phone_number_format_variations_and_normalization():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Normalization Test House", status="ACTIVE", deleted_at=None)

    # Invitation issued with raw format "+91 98765 43210" normalized to "+919876543210"
    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        phone_number="+919876543210",
        role="MEMBER",
        token="tok-norm-1",
        invitation_code="OZ-NRM001",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=5)
    )

    # User registered with local 10-digit format "9876543210"
    user = UserModel(
        id=user_id,
        phone_number="9876543210",
        mobile_verified=True,
        is_active=True
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

    # Acceptance must succeed because normalize_phone_number("9876543210") == "+919876543210"
    res = await accept_invitation("tok-norm-1", current_user=user, db=mock_db, redis_client=mock_redis)
    assert res.data.home_id == home_id
    assert res.data.role == "MEMBER"
    assert invitation.status == "ACCEPTED"


@pytest.mark.asyncio
async def test_unverified_mobile_cannot_accept_mobile_invitation():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Secure Home", status="ACTIVE", deleted_at=None)
    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        phone_number="+15559998888",
        role="MEMBER",
        token="tok-unverified-test",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=5)
    )

    unverified_user = UserModel(
        id=user_id,
        phone_number="+15559998888",
        mobile_verified=False,
        is_active=True
    )

    inv_mock = MagicMock()
    inv_mock.first.return_value = (invitation, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("tok-unverified-test", current_user=unverified_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403
    assert "verify your mobile number" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_expired_and_already_used_invitation_rejection():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Test Home", status="ACTIVE", deleted_at=None)
    user = UserModel(id=user_id, email="user@test.com", is_active=True)

    # Expired
    expired_inv = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        role="MEMBER",
        token="tok-expired",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    inv_mock = MagicMock()
    inv_mock.first.return_value = (expired_inv, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("tok-expired", current_user=user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()

    # Already accepted
    accepted_inv = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        role="MEMBER",
        token="tok-accepted",
        status="ACCEPTED",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    inv_mock.first.return_value = (accepted_inv, home)
    mock_db.execute.return_value = inv_mock

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation("tok-accepted", current_user=user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "already been accepted" in exc_info.value.detail.lower()
