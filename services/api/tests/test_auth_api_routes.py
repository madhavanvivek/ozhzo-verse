import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from src.schemas.auth import RegisterRequest, LoginRequest, RefreshTokenRequest, ResetPasswordRequest
from src.schemas.user import UpdateProfileRequest
from src.api.v1.auth import register, login, refresh_tokens, reset_password
from src.api.v1.users import get_my_profile, update_my_profile, change_my_password
from src.core.security import hash_password
from src.infrastructure.database.models import UserModel, UserProfileModel


@pytest.mark.asyncio
async def test_register_creates_user_and_profile():
    mock_db = AsyncMock()
    # Mock email check returning None (no existing user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    req = RegisterRequest(
        email="test@example.com",
        full_name="Morgan Rivera",
        password="SecurePassword123!"
    )

    res = await register(req, db=mock_db)
    assert res.success is True
    assert res.data.email == "test@example.com"
    assert res.data.access_token is not None
    assert res.data.refresh_token is not None
    assert mock_db.add.call_count >= 2  # Added user and profile


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = UserModel(id=uuid4(), email="existing@example.com")
    mock_db.execute.return_value = mock_result

    req = RegisterRequest(
        email="existing@example.com",
        full_name="Duplicate User",
        password="SecurePassword123!"
    )

    with pytest.raises(HTTPException) as exc_info:
        await register(req, db=mock_db)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_login_success_and_failure():
    mock_db = AsyncMock()
    hashed = hash_password("ValidPassword123!")
    user = UserModel(id=uuid4(), email="valid@example.com", password_hash=hashed, is_active=True)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_result

    # 1. Valid login
    valid_req = LoginRequest(email="valid@example.com", password="ValidPassword123!")
    res = await login(valid_req, db=mock_db)
    assert res.success is True
    assert res.data.access_token is not None

    # 2. Invalid password
    bad_req = LoginRequest(email="valid@example.com", password="WrongPassword!")
    with pytest.raises(HTTPException) as exc_info:
        await login(bad_req, db=mock_db)
    assert exc_info.value.status_code == 401
