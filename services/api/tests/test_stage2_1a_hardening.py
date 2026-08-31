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
    update_home_settings,
    delete_home_workspace
)
from src.api.v1.admin_homes import (
    get_home_detail as admin_get_home_detail,
    admin_regenerate_home_qr,
    admin_revoke_home_qr
)
from src.core.home_identity import generate_unique_public_home_id, generate_home_qr_token
from src.domain.entitlements import check_can_create_home, check_and_reserve_home_member_seat
from src.core.exceptions import TierLimitExceededException, MobileVerificationRequiredException
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
async def test_01_home_id_format_and_entropy():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    home_id = await generate_unique_public_home_id(mock_db)
    assert home_id.startswith("OZH-")
    assert len(home_id) == 10
    suffix = home_id[4:]
    for char in suffix:
        assert char in "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
        assert char not in "0O1IL"


@pytest.mark.asyncio
async def test_02_home_id_collision_retry():
    mock_db = AsyncMock()
    # Simulate collision on first call, uniqueness on second
    mock_res_collision = MagicMock()
    mock_res_collision.scalar_one_or_none.return_value = uuid4()

    mock_res_unique = MagicMock()
    mock_res_unique.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_res_collision, mock_res_unique]

    home_id = await generate_unique_public_home_id(mock_db)
    assert home_id.startswith("OZH-")
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_03_first_free_home_creation_succeeds():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user_id = uuid4()
    user = UserModel(id=user_id, email="firsthome@example.com", mobile_verified=True)

    # No existing homes
    mock_scalars = MagicMock()
    mock_scalars.scalars.return_value.all.return_value = []
    mock_scalars.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_scalars

    payload = CreateHomeRequest(name="My First Home", currency="USD", timezone="UTC")
    res = await create_home(payload, current_user=user, db=mock_db, redis_client=mock_redis)

    assert res.data.name == "My First Home"
    assert res.data.public_home_id.startswith("OZH-")
    assert res.data.home_qr_status == "ACTIVE"
    assert res.data.home_qr_version == 1


@pytest.mark.asyncio
async def test_04_second_home_without_subscription_fails():
    mock_db = AsyncMock()
    user_id = uuid4()
    user = UserModel(id=user_id, email="secondhome@example.com", mobile_verified=True)

    existing_home = HomeModel(id=uuid4(), name="Existing Home", created_by=user_id)

    # Mock execute for checking existing homes and subscriptions
    def mock_exec(stmt):
        q_str = str(stmt)
        res = MagicMock()
        if "subscriptions" in q_str:
            res.scalars.return_value.first.return_value = None
        else:
            res.scalars.return_value.all.return_value = [existing_home]
        return res

    mock_db.execute.side_effect = mock_exec

    with pytest.raises(TierLimitExceededException) as exc_info:
        await check_can_create_home(user, mock_db)
    assert "one Home" in exc_info.value.detail


@pytest.mark.asyncio
async def test_05_second_home_with_active_subscription_succeeds():
    mock_db = AsyncMock()
    user_id = uuid4()
    user = UserModel(id=user_id, email="sub_owner@example.com", mobile_verified=True)

    existing_home = HomeModel(id=uuid4(), name="Existing Home", created_by=user_id)
    active_sub = SubscriptionModel(id=uuid4(), home_id=existing_home.id, status="ACTIVE")

    def mock_exec(stmt):
        q_str = str(stmt)
        res = MagicMock()
        if "subscriptions" in q_str:
            res.scalars.return_value.first.return_value = active_sub
        else:
            res.scalars.return_value.all.return_value = [existing_home]
        return res

    mock_db.execute.side_effect = mock_exec

    # Should not raise exception
    await check_can_create_home(user, mock_db)


@pytest.mark.asyncio
async def test_06_unverified_mobile_cannot_create_home():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    user = UserModel(id=uuid4(), email="unverified@example.com", mobile_verified=False)
    payload = CreateHomeRequest(name="Blocked Home")

    with pytest.raises(MobileVerificationRequiredException):
        await create_home(payload, current_user=user, db=mock_db, redis_client=mock_redis)


@pytest.mark.asyncio
async def test_07_qr_regeneration_and_revocation_lifecycle():
    mock_db = AsyncMock()
    home_id = uuid4()
    user = UserModel(id=uuid4(), email="admin@example.com")
    home = HomeModel(
        id=home_id,
        name="Lifecycle Manor",
        public_home_id="OZH-LIFE01",
        home_qr_token="token-initial-1",
        home_qr_status="ACTIVE",
        home_qr_version=1,
        status="ACTIVE"
    )
    mock_db.get.return_value = home
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    # 1. Regenerate QR
    res_regen = await regenerate_home_qr(home_ctx=ctx, db=mock_db)
    assert res_regen.data.qr_version == 2
    assert res_regen.data.qr_status == "ACTIVE"
    assert res_regen.data.qr_token != "token-initial-1"
    new_token = res_regen.data.qr_token

    # 2. Revoke QR
    res_revoke = await revoke_home_qr(home_ctx=ctx, db=mock_db)
    assert res_revoke.data.qr_status == "REVOKED"
    assert res_revoke.data.qr_revoked_at is not None

    # 3. Resolve revoked QR fails with 400
    mock_res_revoked = MagicMock()
    mock_res_revoked.scalars.return_value.first.return_value = home
    mock_db.execute.return_value = mock_res_revoked

    with pytest.raises(HTTPException) as exc_info:
        await resolve_home_qr(token=new_token, db=mock_db)
    assert exc_info.value.status_code == 400
    assert "revoked" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_08_join_request_concurrency_seat_limit():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    admin_id = uuid4()
    user_a = uuid4()
    user_b = uuid4()

    admin_user = UserModel(id=admin_id, email="admin@example.com")
    ctx = HomeContext(home_id=home_id, user=admin_user, role=ROLE_OWNER)

    # Free tier home with limit of 5 seats; already has 4 members
    # Request A and Request B are both pending
    req_a = HomeJoinRequestModel(id=uuid4(), home_id=home_id, user_id=user_a, status="PENDING")
    req_b = HomeJoinRequestModel(id=uuid4(), home_id=home_id, user_id=user_b, status="PENDING")

    # Step 1: Admin reviews Request A -> current members = 4 < 5 -> approves -> member added (total 5)
    mock_db.get.return_value = req_a

    # Count returns 4 active members initially
    count_mock = MagicMock()
    count_mock.scalar.return_value = 4
    sub_mock = MagicMock()
    sub_mock.scalars.return_value.first.return_value = None
    existing_mem_mock = MagicMock()
    existing_mem_mock.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [count_mock, sub_mock, existing_mem_mock]

    res_a = await review_join_request(req_a.id, ReviewJoinRequestInput(action="APPROVE"), home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res_a.data.status == "APPROVED"

    # Step 2: Admin reviews Request B -> now current members = 5 (limit reached) -> must raise TierLimitExceededException
    mock_db.get.return_value = req_b

    count_mock_full = MagicMock()
    count_mock_full.scalar.return_value = 5

    mock_db.execute.side_effect = [count_mock_full, sub_mock, existing_mem_mock]

    with pytest.raises(TierLimitExceededException) as exc_info:
        await review_join_request(req_b.id, ReviewJoinRequestInput(action="APPROVE"), home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert "seat limit" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_09_archived_home_deletion_revokes_qr():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    user = UserModel(id=uuid4(), email="owner@example.com")
    home = HomeModel(id=home_id, name="To Archive", home_qr_token="active-tok", home_qr_status="ACTIVE", status="ACTIVE")

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = home
    mock_db.execute.return_value = mock_res

    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    res = await delete_home_workspace(home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert "archived" in res.data.message.lower()
    assert home.status == "SUSPENDED"
    assert home.home_qr_status == "REVOKED"
    assert home.deleted_at is not None


@pytest.mark.asyncio
async def test_10_super_admin_home_inspection_and_qr_management():
    mock_db = AsyncMock()
    home_id = uuid4()
    super_admin = UserModel(id=uuid4(), email="admin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")

    home = HomeModel(
        id=home_id,
        name="Inspected Estate",
        public_home_id="OZH-ADMIN1",
        home_qr_token="tok-v1",
        home_qr_status="ACTIVE",
        home_qr_version=1,
        created_by=uuid4(),
        status="ACTIVE"
    )

    mock_db.get.return_value = home

    # Admin regenerate QR
    res_regen = await admin_regenerate_home_qr(home_id=home_id, super_admin=super_admin, db=mock_db)
    assert "version 2" in res_regen.data.message
    assert home.home_qr_version == 2

    # Admin revoke QR
    res_revoke = await admin_revoke_home_qr(home_id=home_id, super_admin=super_admin, db=mock_db)
    assert "revoked" in res_revoke.data.message
    assert home.home_qr_status == "REVOKED"
