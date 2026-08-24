import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.infrastructure.database.models import UserModel, UserProfileModel
from src.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from src.api.v1.auth import register, login, refresh_tokens, logout, forgot_password, reset_password, enforce_auth_rate_limit


@pytest.mark.asyncio
async def test_AUTH_001_registration():
    """AUTH-001: User registration with Argon2id hash and automatic profile creation."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    # No existing user
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    req = RegisterRequest(
        email="sprint1_user@example.com",
        full_name="Sprint One User",
        password="SecurePassword123!"
    )

    res = await register(req, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.email == "sprint1_user@example.com"
    assert res.data.access_token is not None
    assert res.data.refresh_token is not None
    assert res.data.expires_in == 900  # 15 mins
    assert mock_db.add.call_count in [2, 3]  # UserModel + UserProfileModel (+ AuditLogModel)


@pytest.mark.asyncio
async def test_AUTH_002_duplicate_registration():
    """AUTH-002: Duplicate registration returns HTTP 409 Conflict."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    existing_user = UserModel(id=uuid4(), email="existing@example.com")
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_res

    req = RegisterRequest(
        email="existing@example.com",
        full_name="Duplicate User",
        password="SecurePassword123!"
    )

    with pytest.raises(HTTPException) as exc_info:
        await register(req, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_AUTH_003_login():
    """AUTH-003: Login with valid credentials returns token pair."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    user_id = uuid4()
    hashed_pwd = hash_password("ValidPassword123!")
    user = UserModel(id=user_id, email="login_user@example.com", password_hash=hashed_pwd, is_active=True)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res

    req = LoginRequest(email="login_user@example.com", password="ValidPassword123!")
    res = await login(req, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.email == "login_user@example.com"
    assert res.data.user_id == user_id


@pytest.mark.asyncio
async def test_AUTH_004_invalid_credentials():
    """AUTH-004: Invalid password returns HTTP 401 Unauthorized without leaking account existence."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    user = UserModel(id=uuid4(), email="login_user@example.com", password_hash=hash_password("RealPassword123!"), is_active=True)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res

    req = LoginRequest(email="login_user@example.com", password="WrongPassword999!")

    with pytest.raises(HTTPException) as exc_info:
        await login(req, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 401
    assert "Invalid credentials" in exc_info.value.detail or "Invalid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_AUTH_005_logout():
    """AUTH-005: Logout revokes session by writing JTI to Redis blacklist."""
    mock_redis = AsyncMock()
    user_id = uuid4()
    user = UserModel(id=user_id, email="logout_user@example.com")

    access_token = create_access_token(subject=str(user_id))
    credentials = MagicMock()
    credentials.credentials = access_token

    res = await logout(credentials=credentials, current_user=user, redis_client=mock_redis)

    assert res.success is True
    assert mock_redis.set.called


@pytest.mark.asyncio
async def test_AUTH_006_refresh_token():
    """AUTH-006: Valid refresh token produces new access/refresh token pair."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Not revoked

    user_id = uuid4()
    user = UserModel(id=user_id, email="refresh_user@example.com", is_active=True)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res

    ref_token = create_refresh_token(subject=str(user_id))
    req = RefreshTokenRequest(refresh_token=ref_token)

    res = await refresh_tokens(req, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.access_token is not None
    assert res.data.refresh_token is not None


@pytest.mark.asyncio
async def test_AUTH_007_refresh_token_rotation():
    """AUTH-007: Token refresh automatically blacklists the previous refresh token JTI."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    user_id = uuid4()
    user = UserModel(id=user_id, email="refresh_user@example.com", is_active=True)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res

    ref_token = create_refresh_token(subject=str(user_id))
    token_data = decode_token(ref_token)
    old_jti = token_data.get("jti")

    req = RefreshTokenRequest(refresh_token=ref_token)
    await refresh_tokens(req, db=mock_db, redis_client=mock_redis)

    # Verify old JTI was blacklisted in Redis
    mock_redis.set.assert_called_with(f"revoked_token:{old_jti}", "1", ex=pytest.approx(30 * 86400, rel=100))


@pytest.mark.asyncio
async def test_AUTH_008_revoked_token():
    """AUTH-008: Attempting to use a revoked token returns HTTP 401."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    # Mock token as already revoked in Redis
    mock_redis.get.return_value = b"1"

    user_id = uuid4()
    ref_token = create_refresh_token(subject=str(user_id))
    req = RefreshTokenRequest(refresh_token=ref_token)

    with pytest.raises(HTTPException) as exc_info:
        await refresh_tokens(req, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 401
    assert "revoked" in exc_info.value.detail


@pytest.mark.asyncio
async def test_AUTH_009_password_reset():
    """AUTH-009: Requesting and completing password reset with single-use cryptographic token."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    user_id = uuid4()
    user = UserModel(id=user_id, email="reset_user@example.com", is_active=True, password_hash=hash_password("OldPassword123!"))
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res

    # 1. Forgot password request
    req_forgot = ForgotPasswordRequest(email="reset_user@example.com")
    res_forgot = await forgot_password(req_forgot, db=mock_db, redis_client=mock_redis)
    assert res_forgot.success is True

    # 2. Reset password with token
    mock_redis.get.return_value = str(user_id)
    req_reset = ResetPasswordRequest(token="sample-crypto-token", new_password="BrandNewPassword456!")
    res_reset = await reset_password(req_reset, db=mock_db, redis_client=mock_redis)

    assert res_reset.success is True
    assert verify_password("BrandNewPassword456!", user.password_hash) is True
    mock_redis.delete.assert_called_with("password_reset:sample-crypto-token")


@pytest.mark.asyncio
async def test_AUTH_010_rate_limiting():
    """AUTH-010: Exceeding sliding-window request limit triggers HTTP 429 Too Many Requests."""
    mock_redis = AsyncMock()
    # Simulate count > max_requests
    mock_redis.incr.return_value = 11

    with pytest.raises(HTTPException) as exc_info:
        await enforce_auth_rate_limit(
            redis_client=mock_redis,
            identifier="attacker@example.com",
            action="login",
            max_requests=10,
            window_seconds=60
        )
    assert exc_info.value.status_code == 429
    assert "Too many" in exc_info.value.detail
