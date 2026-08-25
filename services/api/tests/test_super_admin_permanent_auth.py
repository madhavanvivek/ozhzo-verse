import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi import HTTPException

from src.core.config import settings
from src.core.security import hash_password, verify_password, create_access_token, decode_token
from src.infrastructure.database.models import UserModel
from src.api.v1.auth import login
from src.schemas.auth import LoginRequest
from src.api.dependencies import require_super_admin


@pytest.mark.asyncio
async def test_01_valid_super_admin_credentials_succeed():
    """TEST 1: Valid Super Admin credentials (vivek@zinfog.com + Caseno@123) succeed."""
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
    mock_res.scalars.return_value.first.return_value = user
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="vivek@zinfog.com", password="Caseno@123")
    res = await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None
    assert res.data.email == "vivek@zinfog.com"


@pytest.mark.asyncio
async def test_02_invalid_super_admin_password_rejected():
    """TEST 2: Invalid Super Admin password returns 401."""
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
    mock_res.scalars.return_value.first.return_value = user
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="vivek@zinfog.com", password="WrongPassword123")
    with pytest.raises(HTTPException) as exc:
        await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_03_unknown_email_rejected():
    """TEST 3: Unknown email returns 401."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="nonexistent@example.com", password="SomePassword123")
    with pytest.raises(HTTPException) as exc:
        await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_04_valid_normal_user_login_succeeds():
    """TEST 4: Valid normal user credentials succeed."""
    user = UserModel(
        id=uuid4(),
        email="regular@example.com",
        password_hash=hash_password("UserPass123!"),
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = user
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="regular@example.com", password="UserPass123!")
    res = await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None


@pytest.mark.asyncio
async def test_05_normal_user_attempting_admin_api_blocked():
    """TEST 5: Normal user attempting admin API is blocked with 403."""
    user = UserModel(
        id=uuid4(),
        email="regular@example.com",
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    with pytest.raises(HTTPException) as exc:
        await require_super_admin(current_user=user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_06_super_admin_accessing_admin_api_allowed():
    """TEST 6: Super Admin accessing admin API is allowed."""
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN"
    )

    result_user = await require_super_admin(current_user=user)
    assert result_user.id == user.id


@pytest.mark.asyncio
async def test_07_super_admin_token_generation_and_decode():
    """TEST 7: Super Admin token correctly decodes and validates."""
    uid = str(uuid4())
    token = create_access_token(subject=uid)
    decoded = decode_token(token)
    assert decoded["sub"] == uid
    assert decoded["type"] == "access"


@pytest.mark.asyncio
async def test_08_super_admin_self_heals_hash_on_fallback():
    """TEST 8: Super Admin with outdated hash authenticates via fallback and self-heals hash."""
    user = UserModel(
        id=uuid4(),
        email="vivek@zinfog.com",
        password_hash="outdated_or_mismatched_hash",
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = user
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    payload = LoginRequest(email="vivek@zinfog.com", password="Caseno@123")
    res = await login(payload=payload, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert user.is_super_admin is True
    assert user.system_role == "SUPER_ADMIN"
    assert verify_password("Caseno@123", user.password_hash) is True
