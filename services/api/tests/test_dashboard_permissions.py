import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.api.dependencies import require_home_permission
from src.core.exceptions import PermissionDeniedException
from src.domain.permissions import (
    ROLE_OWNER,
    ROLE_HOME_ADMIN,
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_CHILD,
    ROLE_GUEST,
    has_permission
)
from src.infrastructure.database.models import HomeMemberModel, UserModel


def test_dashboard_permission_matrix():
    """Verify that all valid household roles have the canonical 'dashboard:view' permission."""
    assert has_permission(ROLE_OWNER, "dashboard:view") is True
    assert has_permission(ROLE_HOME_ADMIN, "dashboard:view") is True
    assert has_permission(ROLE_ADMIN, "dashboard:view") is True
    assert has_permission(ROLE_MEMBER, "dashboard:view") is True
    assert has_permission(ROLE_CHILD, "dashboard:view") is True
    assert has_permission(ROLE_GUEST, "dashboard:view") is True
    assert has_permission("UNKNOWN_ROLE", "dashboard:view") is False


@pytest.mark.asyncio
async def test_owner_can_access_dashboard():
    """Verify OWNER can access the dashboard endpoint using require_home_permission('dashboard:view')."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    owner_user = UserModel(id=uuid4(), email="owner@example.com")

    owner_membership = HomeMemberModel(
        home_id=home_id,
        user_id=owner_user.id,
        role=ROLE_OWNER,
        status="ACTIVE"
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = owner_membership
    mock_db.execute.return_value = mock_res

    checker = require_home_permission("dashboard:view")
    ctx = await checker(home_id=home_id, current_user=owner_user, db=mock_db, redis_client=mock_redis)

    assert ctx.home_id == home_id
    assert ctx.role == ROLE_OWNER
    assert ctx.user.id == owner_user.id


@pytest.mark.asyncio
async def test_home_admin_can_access_dashboard():
    """Verify HOME_ADMIN can access the dashboard endpoint using require_home_permission('dashboard:view')."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    admin_user = UserModel(id=uuid4(), email="admin@example.com")

    admin_membership = HomeMemberModel(
        home_id=home_id,
        user_id=admin_user.id,
        role=ROLE_HOME_ADMIN,
        status="ACTIVE"
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = admin_membership
    mock_db.execute.return_value = mock_res

    checker = require_home_permission("dashboard:view")
    ctx = await checker(home_id=home_id, current_user=admin_user, db=mock_db, redis_client=mock_redis)

    assert ctx.home_id == home_id
    assert ctx.role == ROLE_HOME_ADMIN
    assert ctx.user.id == admin_user.id


@pytest.mark.asyncio
async def test_non_member_rejected_from_dashboard():
    """Verify non-member receives 403 Forbidden when attempting to access the dashboard."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    foreign_user = UserModel(id=uuid4(), email="unauthorized@example.com")

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    checker = require_home_permission("dashboard:view")
    with pytest.raises(HTTPException) as exc_info:
        await checker(home_id=home_id, current_user=foreign_user, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
