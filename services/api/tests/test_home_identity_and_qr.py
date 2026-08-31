import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER
from src.api.dependencies import HomeContext
from src.api.v1.homes import (
    create_home,
    get_home_details,
    get_home_identity,
    regenerate_home_qr,
    revoke_home_qr,
    resolve_home_qr,
    create_join_request,
    list_home_join_requests,
    review_join_request,
    update_home_settings
)
from src.core.home_identity import generate_unique_public_home_id, generate_home_qr_token
from src.core.exceptions import TierLimitExceededException
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    HomeJoinRequestModel,
    SubscriptionModel,
    UserModel,
    UserProfileModel
)
from src.schemas.home import (
    CreateHomeRequest,
    CreateJoinRequestInput,
    ReviewJoinRequestInput,
    UpdateHomeRequest
)


@pytest.mark.asyncio
async def test_01_public_id_format_and_collision_resistance():
    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = res_mock

    public_id = await generate_unique_public_home_id(mock_db)
    assert public_id.startswith("OZH-")
    assert len(public_id) == 10
    suffix = public_id[4:]
    assert len(suffix) == 6
    for char in suffix:
        assert char in "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
        assert char not in "0O1IL"


@pytest.mark.asyncio
async def test_02_qr_token_generation_and_entropy():
    tok1 = generate_home_qr_token()
    tok2 = generate_home_qr_token()
    assert tok1 != tok2
    assert len(tok1) >= 40


@pytest.mark.asyncio
async def test_03_create_home_generates_identity_and_qr():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    user = UserModel(id=user_id, email="owner@example.com", mobile_verified=True)

    mock_scalars = MagicMock()
    mock_scalars.scalars.return_value.all.return_value = []
    mock_scalars.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_scalars

    payload = CreateHomeRequest(name="Alpha Haven", currency="USD", timezone="UTC")
    res = await create_home(payload, current_user=user, db=mock_db, redis_client=mock_redis)
    data = res.data

    assert data.name == "Alpha Haven"
    assert data.public_home_id.startswith("OZH-")
    assert data.home_qr_status == "ACTIVE"
    assert data.home_qr_version == 1
    assert data.home_qr_url.startswith("/join/home/")


@pytest.mark.asyncio
async def test_04_rename_home_preserves_public_home_id():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    user = UserModel(id=user_id, email="owner@example.com")

    home = HomeModel(
        id=home_id,
        name="Old Manor",
        public_home_id="OZH-999XYZ",
        home_qr_token="secure-token-123",
        home_qr_status="ACTIVE",
        home_qr_version=1,
        created_by=user_id
    )

    mock_scalars = MagicMock()
    mock_scalars.scalar_one_or_none.return_value = home
    mock_db.execute.return_value = mock_scalars

    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    payload = UpdateHomeRequest(name="New Palace")

    res = await update_home_settings(payload, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    data = res.data

    assert data.name == "New Palace"
    assert data.public_home_id == "OZH-999XYZ"


@pytest.mark.asyncio
async def test_05_resolve_active_qr_token_returns_safe_public_info():
    mock_db = AsyncMock()
    home_id = uuid4()
    owner_id = uuid4()

    owner = UserModel(id=owner_id, email="creator@example.com")
    owner.profile = UserProfileModel(user_id=owner_id, display_name="Grace Hopper")

    home = HomeModel(
        id=home_id,
        name="Grace House",
        public_home_id="OZH-GH7777",
        home_qr_token="valid-qr-token",
        home_qr_status="ACTIVE",
        status="ACTIVE",
        created_by=owner_id
    )
    home.members = [HomeMemberModel(id=uuid4(), home_id=home_id, user_id=owner_id, role="OWNER", status="ACTIVE")]

    def mock_execute(stmt):
        query_str = str(stmt)
        res = MagicMock()
        if "users" in query_str:
            res.scalars.return_value.first.return_value = owner
        else:
            res.scalars.return_value.first.return_value = home
        return res

    mock_db.execute.side_effect = mock_execute

    res = await resolve_home_qr(token="valid-qr-token", db=mock_db)
    data = res.data

    assert data.home_name == "Grace House"
    assert data.public_home_id == "OZH-GH7777"
    assert data.owner_name == "Grace Hopper"
    assert data.member_count == 1
    assert data.qr_status == "ACTIVE"


@pytest.mark.asyncio
async def test_06_resolve_revoked_qr_token_is_rejected():
    mock_db = AsyncMock()
    home = HomeModel(
        id=uuid4(),
        name="Revoked Home",
        public_home_id="OZH-REVOK1",
        home_qr_token="old-revoked-token",
        home_qr_status="REVOKED",
        status="ACTIVE"
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = home
    mock_db.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc_info:
        await resolve_home_qr(token="old-revoked-token", db=mock_db)
    assert exc_info.value.status_code == 400
    assert "revoked" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_07_regenerate_home_qr_invalidates_previous():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    user = UserModel(id=user_id, email="owner@example.com")

    home = HomeModel(
        id=home_id,
        name="Regen Castle",
        public_home_id="OZH-REG111",
        home_qr_token="token-v1",
        home_qr_status="ACTIVE",
        home_qr_version=1,
        created_by=user_id
    )
    mock_db.get.return_value = home

    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    res = await regenerate_home_qr(home_ctx=ctx, db=mock_db)
    data = res.data

    assert data.qr_token != "token-v1"
    assert data.qr_version == 2
    assert data.qr_status == "ACTIVE"
    assert home.home_qr_token == data.qr_token


@pytest.mark.asyncio
async def test_08_revoke_home_qr():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    user = UserModel(id=user_id, email="owner@example.com")

    home = HomeModel(
        id=home_id,
        name="Revoke Castle",
        public_home_id="OZH-RVK222",
        home_qr_token="active-tok",
        home_qr_status="ACTIVE",
        home_qr_version=1,
        created_by=user_id
    )
    mock_db.get.return_value = home

    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    res = await revoke_home_qr(home_ctx=ctx, db=mock_db)
    data = res.data

    assert data.qr_status == "REVOKED"
    assert data.qr_revoked_at is not None
    assert home.home_qr_status == "REVOKED"


@pytest.mark.asyncio
async def test_09_create_join_request_lifecycle():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    applicant = UserModel(id=user_id, email="applicant@example.com")
    applicant.profile = UserProfileModel(user_id=user_id, display_name="New Applicant")

    home = HomeModel(
        id=home_id,
        name="Welcoming Home",
        public_home_id="OZH-WELC01",
        home_qr_token="join-tok-123",
        home_qr_status="ACTIVE",
        status="ACTIVE"
    )

    def mock_execute(stmt):
        q_str = str(stmt)
        res = MagicMock()
        if "home_members" in q_str:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
        elif "home_join_requests" in q_str:
            res.scalars.return_value.first.return_value = None
        else:
            res.scalars.return_value.first.return_value = home
        return res

    mock_db.execute.side_effect = mock_execute

    payload = CreateJoinRequestInput(message="Hi, I moved into apartment 4B!")
    res = await create_join_request(token="join-tok-123", payload=payload, current_user=applicant, db=mock_db)
    data = res.data

    assert data.home_id == home_id
    assert data.user_id == user_id
    assert data.status == "PENDING"
    assert data.message == "Hi, I moved into apartment 4B!"


@pytest.mark.asyncio
async def test_10_existing_member_cannot_create_join_request():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    member = UserModel(id=user_id, email="existing@example.com")

    home = HomeModel(id=home_id, name="My Home", home_qr_token="tok", home_qr_status="ACTIVE", status="ACTIVE")
    existing_mem = HomeMemberModel(home_id=home_id, user_id=user_id, role="MEMBER", status="ACTIVE")

    def mock_execute(stmt):
        q_str = str(stmt)
        res = MagicMock()
        if "home_members" in q_str:
            res.scalars.return_value.first.return_value = existing_mem
        else:
            res.scalars.return_value.first.return_value = home
        return res

    mock_db.execute.side_effect = mock_execute

    with pytest.raises(HTTPException) as exc_info:
        await create_join_request(token="tok", payload=CreateJoinRequestInput(), current_user=member, db=mock_db)
    assert exc_info.value.status_code == 400
    assert "already an active member" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_11_admin_review_approve_adds_member():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    admin_id = uuid4()
    applicant_id = uuid4()
    req_id = uuid4()

    admin = UserModel(id=admin_id, email="admin@example.com")
    home = HomeModel(id=home_id, name="Approval Villa", status="ACTIVE")
    ctx = HomeContext(home_id=home_id, user=admin, role=ROLE_ADMIN)

    join_req = HomeJoinRequestModel(
        id=req_id,
        home_id=home_id,
        user_id=applicant_id,
        status="PENDING",
        created_at=datetime.now(timezone.utc)
    )
    mock_db.get.return_value = join_req

    mock_scalars = MagicMock()
    mock_scalars.scalar.return_value = 1
    mock_scalars.scalars.return_value.first.return_value = SubscriptionModel(home_id=home_id, paid_member_seats=5)
    mock_db.execute.return_value = mock_scalars

    payload = ReviewJoinRequestInput(action="APPROVE", role="MEMBER")
    res = await review_join_request(
        request_id=req_id,
        payload=payload,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )
    data = res.data

    assert data.status == "APPROVED"
    assert join_req.status == "APPROVED"
    assert join_req.reviewed_by == admin_id


@pytest.mark.asyncio
async def test_12_admin_review_reject():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    admin_id = uuid4()
    applicant_id = uuid4()
    req_id = uuid4()

    admin = UserModel(id=admin_id, email="admin@example.com")
    home = HomeModel(id=home_id, name="Rejection Villa", status="ACTIVE")
    ctx = HomeContext(home_id=home_id, user=admin, role=ROLE_ADMIN)

    join_req = HomeJoinRequestModel(
        id=req_id,
        home_id=home_id,
        user_id=applicant_id,
        status="PENDING",
        created_at=datetime.now(timezone.utc)
    )
    mock_db.get.return_value = join_req

    payload = ReviewJoinRequestInput(action="REJECT")
    res = await review_join_request(
        request_id=req_id,
        payload=payload,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )
    data = res.data

    assert data.status == "REJECTED"
    assert join_req.status == "REJECTED"
    assert join_req.reviewed_by == admin_id
