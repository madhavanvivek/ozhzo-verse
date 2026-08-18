import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.core.security import hash_password
from src.infrastructure.database.models import UserModel, UserProfileModel
from src.schemas.auth import ChangePasswordRequest
from src.schemas.user import UpdateProfileRequest
from src.api.v1.users import get_my_profile, update_my_profile, change_my_password


@pytest.mark.asyncio
async def test_get_my_profile():
    mock_db = AsyncMock()
    user_id = uuid4()
    profile = UserProfileModel(
        user_id=user_id,
        display_name="Alex Rivera",
        timezone="America/New_York",
        preferred_language="en"
    )
    user = UserModel(
        id=user_id,
        email="alex@example.com",
        is_active=True,
        is_verified=True,
        profile=profile
    )

    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=user, db=mock_db)

    assert res.success is True
    assert res.data.email == "alex@example.com"
    assert res.data.display_name == "Alex Rivera"
    assert res.data.timezone == "America/New_York"
    assert res.data.is_super_admin is False
    assert res.data.system_role == "USER"
    assert not hasattr(res.data, "password_hash")
    assert not hasattr(res.data, "password")


@pytest.mark.asyncio
async def test_get_my_profile_super_admin():
    mock_db = AsyncMock()
    user_id = uuid4()
    profile = UserProfileModel(
        user_id=user_id,
        display_name="Super Admin User",
        timezone="UTC",
        preferred_language="en"
    )
    user = UserModel(
        id=user_id,
        email="superadmin@ozhzo.com",
        is_active=True,
        is_verified=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN",
        profile=profile
    )

    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=user, db=mock_db)

    assert res.success is True
    assert res.data.email == "superadmin@ozhzo.com"
    assert res.data.is_super_admin is True
    assert res.data.system_role == "SUPER_ADMIN"
    assert not hasattr(res.data, "password_hash")


@pytest.mark.asyncio
async def test_get_my_profile_household_owner_not_super_admin():
    """Household OWNER is a household role, not a platform role. is_super_admin must be False and system_role USER."""
    mock_db = AsyncMock()
    user_id = uuid4()
    profile = UserProfileModel(
        user_id=user_id,
        display_name="Household Owner",
        timezone="UTC",
        preferred_language="en"
    )
    user = UserModel(
        id=user_id,
        email="owner@ozhzo.com",
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        system_role="USER",
        profile=profile
    )

    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=user, db=mock_db)

    assert res.success is True
    assert res.data.is_super_admin is False
    assert res.data.system_role == "USER"


@pytest.mark.asyncio
async def test_update_my_profile():
    mock_db = AsyncMock()
    user_id = uuid4()
    profile = UserProfileModel(
        user_id=user_id,
        display_name="Alex Rivera",
        timezone="UTC"
    )
    user = UserModel(
        id=user_id,
        email="alex@example.com",
        profile=profile
    )

    req = UpdateProfileRequest(
        display_name="Alex R.",
        timezone="Europe/London",
        phone_number="+15551234567"
    )

    res = await update_my_profile(req, current_user=user, db=mock_db)

    assert res.success is True
    assert profile.display_name == "Alex R."
    assert profile.timezone == "Europe/London"
    assert profile.phone_number == "+15551234567"


@pytest.mark.asyncio
async def test_change_my_password_success():
    mock_db = AsyncMock()
    user_id = uuid4()
    user = UserModel(
        id=user_id,
        email="alex@example.com",
        password_hash=hash_password("OldPassword123!")
    )

    req = ChangePasswordRequest(
        current_password="OldPassword123!",
        new_password="NewSecurePassword456!"
    )

    res = await change_my_password(req, current_user=user, db=mock_db)
    assert res.success is True


@pytest.mark.asyncio
async def test_change_my_password_invalid_current():
    mock_db = AsyncMock()
    user_id = uuid4()
    user = UserModel(
        id=user_id,
        email="alex@example.com",
        password_hash=hash_password("OldPassword123!")
    )

    req = ChangePasswordRequest(
        current_password="WrongPassword999!",
        new_password="NewSecurePassword456!"
    )

    with pytest.raises(HTTPException) as exc_info:
        await change_my_password(req, current_user=user, db=mock_db)
    assert exc_info.value.status_code == 400
