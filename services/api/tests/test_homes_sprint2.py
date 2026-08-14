import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.core.exceptions import TierLimitExceededException
from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.home import CreateHomeRequest, UpdateHomeRequest
from src.api.v1.homes import create_home, get_home_details, update_home_settings, delete_home_workspace
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import HomeModel, UserModel


@pytest.mark.asyncio
async def test_create_home_assigns_owner():
    mock_db = AsyncMock()
    # Mock no existing owned homes for user
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    user = UserModel(id=uuid4(), email="owner@example.com")
    req = CreateHomeRequest(
        name="Sunnyvale Villa",
        currency="USD",
        timezone="America/Los_Angeles"
    )

    mock_redis = AsyncMock()
    res = await create_home(req, current_user=user, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.name == "Sunnyvale Villa"
    assert res.data.role == "OWNER"
    assert res.data.currency == "USD"
    # Should add Home, Membership, and 6 default categories = 8 additions
    assert mock_db.add.call_count >= 8


@pytest.mark.asyncio
async def test_create_home_free_tier_limit():
    mock_db = AsyncMock()
    # Mock 1 existing owned home
    existing_home = HomeModel(id=uuid4(), name="Existing Home", created_by=uuid4())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existing_home]
    mock_db.execute.return_value = mock_result

    user = UserModel(id=uuid4(), email="owner@example.com")
    req = CreateHomeRequest(name="Second Home")
    mock_redis = AsyncMock()

    with pytest.raises(TierLimitExceededException):
        await create_home(req, current_user=user, db=mock_db, redis_client=mock_redis)


@pytest.mark.asyncio
async def test_update_home_settings():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    home = HomeModel(id=home_id, name="Old Home Name", currency="USD", timezone="UTC", created_by=user_id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = home
    mock_db.execute.return_value = mock_result

    user = UserModel(id=user_id, email="owner@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")
    req = UpdateHomeRequest(name="Updated Home Name", currency="EUR")
    mock_redis = AsyncMock()

    res = await update_home_settings(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.name == "Updated Home Name"
    assert res.data.currency == "EUR"


@pytest.mark.asyncio
async def test_delete_home_soft_deletion():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    home = HomeModel(id=home_id, name="Home To Archive", created_by=user_id, deleted_at=None)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = home
    mock_db.execute.return_value = mock_result

    user = UserModel(id=user_id, email="owner@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")
    mock_redis = AsyncMock()

    res = await delete_home_workspace(home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert home.deleted_at is not None


def test_home_management_rbac_permissions():
    # Only OWNER can delete home
    assert has_permission(ROLE_OWNER, "home:delete") is True
    assert has_permission(ROLE_ADMIN, "home:delete") is False
    assert has_permission(ROLE_MEMBER, "home:delete") is False
    assert has_permission(ROLE_CHILD, "home:delete") is False
    assert has_permission(ROLE_GUEST, "home:delete") is False

    # OWNER and ADMIN can edit home settings
    assert has_permission(ROLE_OWNER, "home:edit") is True
    assert has_permission(ROLE_ADMIN, "home:edit") is True
    assert has_permission(ROLE_MEMBER, "home:edit") is False
    assert has_permission(ROLE_CHILD, "home:edit") is False
    assert has_permission(ROLE_GUEST, "home:edit") is False

    # All active roles can view home profile
    assert has_permission(ROLE_OWNER, "home:view") is True
    assert has_permission(ROLE_ADMIN, "home:view") is True
    assert has_permission(ROLE_MEMBER, "home:view") is True
    assert has_permission(ROLE_CHILD, "home:view") is True
    assert has_permission(ROLE_GUEST, "home:view") is True
