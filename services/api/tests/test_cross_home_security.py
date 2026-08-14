import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.api.dependencies import require_home_permission
from src.core.exceptions import PermissionDeniedException
from src.domain.permissions import (
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_CHILD,
    ROLE_GUEST,
    has_permission
)
from src.infrastructure.database.models import HomeMemberModel, UserModel


@pytest.mark.asyncio
async def test_non_member_access_rejected():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    foreign_user = UserModel(id=uuid4(), email="attacker@example.com")

    # User is not a member of this home
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    checker = require_home_permission("inventory:view")

    with pytest.raises(HTTPException) as exc_info:
        await checker(home_id=home_id, current_user=foreign_user, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_guest_role_escalation_attempt_fails():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    home_id = uuid4()
    guest_user = UserModel(id=uuid4(), email="guest@example.com")

    guest_membership = HomeMemberModel(
        home_id=home_id,
        user_id=guest_user.id,
        role=ROLE_GUEST,
        status="ACTIVE"
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = guest_membership
    mock_db.execute.return_value = mock_res

    # Guest tries to access bills:view
    checker_bills = require_home_permission("bills:view")
    with pytest.raises(PermissionDeniedException):
        await checker_bills(home_id=home_id, current_user=guest_user, db=mock_db, redis_client=mock_redis)

    # Guest tries to invite new members
    checker_invite = require_home_permission("members:invite")
    with pytest.raises(PermissionDeniedException):
        await checker_invite(home_id=home_id, current_user=guest_user, db=mock_db, redis_client=mock_redis)

    # Guest tries to delete home
    checker_delete_home = require_home_permission("homes:delete")
    with pytest.raises(PermissionDeniedException):
        await checker_delete_home(home_id=home_id, current_user=guest_user, db=mock_db, redis_client=mock_redis)


def test_complete_rbac_matrix():
    # Owner can do all actions
    all_actions = [
        "homes:view", "homes:edit", "homes:delete", "homes:admin",
        "members:invite", "members:manage", "members:remove",
        "inventory:view", "inventory:create", "inventory:edit", "inventory:delete",
        "shopping:view", "shopping:create", "shopping:edit", "shopping:check", "shopping:delete",
        "tasks:view", "tasks:create", "tasks:edit", "tasks:complete", "tasks:delete",
        "bills:view", "bills:create", "bills:edit", "bills:pay", "bills:delete",
        "events:view", "events:create", "events:edit", "events:delete"
    ]
    for action in all_actions:
        assert has_permission(ROLE_OWNER, action) is True

    # Child restrictions
    assert has_permission(ROLE_CHILD, "bills:view") is False
    assert has_permission(ROLE_CHILD, "bills:pay") is False
    assert has_permission(ROLE_CHILD, "homes:delete") is False
    assert has_permission(ROLE_CHILD, "tasks:complete") is True
    assert has_permission(ROLE_CHILD, "shopping:check") is True

    # Guest restrictions
    assert has_permission(ROLE_GUEST, "bills:view") is False
    assert has_permission(ROLE_GUEST, "members:invite") is False
    assert has_permission(ROLE_GUEST, "tasks:complete") is True
    assert has_permission(ROLE_GUEST, "shopping:check") is True
