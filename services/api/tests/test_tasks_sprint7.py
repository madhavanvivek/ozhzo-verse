import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.task import CreateTaskRequest, UpdateTaskRequest
from src.api.v1.tasks import (
    create_task,
    update_task,
    complete_task,
    reopen_task,
    delete_task,
    calculate_next_due_date
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import TaskModel, UserModel, UserProfileModel


def test_recurring_task_due_calculation():
    now = datetime.now(timezone.utc)
    daily_due = calculate_next_due_date(now, "DAILY")
    assert (daily_due - now).days == 1

    weekly_due = calculate_next_due_date(now, "WEEKLY")
    assert (weekly_due - now).days == 7

    monthly_due = calculate_next_due_date(now, "MONTHLY")
    assert (monthly_due - now).days == 30


@pytest.mark.asyncio
async def test_create_task_with_assignment_notification():
    mock_db = AsyncMock()
    home_id = uuid4()
    creator_id = uuid4()
    assigned_user_id = uuid4()

    creator_profile = UserProfileModel(user_id=creator_id, display_name="Alex")
    creator = UserModel(id=creator_id, email="alex@example.com", profile=creator_profile)
    ctx = HomeContext(home_id=home_id, user=creator, role=ROLE_OWNER)

    req = CreateTaskRequest(
        title="Mop kitchen floor",
        description="Use microfiber mop",
        priority="HIGH",
        assigned_to=assigned_user_id,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
        recurrence_rule="WEEKLY"
    )

    from src.infrastructure.database.models import HomeMemberModel
    mock_mem_res = MagicMock()
    mock_mem_res.scalar_one_or_none.return_value = HomeMemberModel(home_id=home_id, user_id=assigned_user_id, status="ACTIVE")
    mock_pref_res = MagicMock()
    mock_pref_res.scalar_one_or_none.return_value = None
    mock_dedup_res = MagicMock()
    mock_dedup_res.scalars.return_value.first.return_value = None
    mock_dedup_res.first.return_value = None
    mock_db.execute.side_effect = [mock_mem_res, mock_pref_res, mock_dedup_res]


    mock_redis = AsyncMock()
    res = await create_task(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)


    assert res.success is True
    assert res.data.title == "Mop kitchen floor"
    assert res.data.priority == "HIGH"
    assert res.data.status == "TODO"
    assert res.data.assigned_to == assigned_user_id
    # Added TaskModel AND NotificationModel record
    assert mock_db.add.call_count >= 2


@pytest.mark.asyncio
async def test_complete_recurring_task_spawns_next():
    mock_db = AsyncMock()
    home_id = uuid4()
    task_id = uuid4()
    user_id = uuid4()

    due = datetime.now(timezone.utc)
    task = TaskModel(
        id=task_id,
        home_id=home_id,
        title="Water plants",
        status="TODO",
        priority="MEDIUM",
        due_date=due,
        recurrence_rule="DAILY",
        created_by=user_id,
        completed_at=None
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = task
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await complete_task(task_id, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert task.status == "COMPLETED"
    assert task.completed_at is not None
    # Added the next recurring iteration of task
    assert mock_db.add.call_count >= 1


@pytest.mark.asyncio
async def test_reopen_task_clears_completed_timestamp():
    mock_db = AsyncMock()
    home_id = uuid4()
    task_id = uuid4()
    user_id = uuid4()

    task = TaskModel(
        id=task_id,
        home_id=home_id,
        title="Vacuum rug",
        status="COMPLETED",
        completed_at=datetime.now(timezone.utc),
        created_by=user_id
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = task
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await reopen_task(task_id, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert task.status == "TODO"
    assert task.completed_at is None


def test_tasks_rbac_permissions():
    # Child & Guest can complete chores
    assert has_permission(ROLE_CHILD, "tasks:complete") is True
    assert has_permission(ROLE_GUEST, "tasks:complete") is True

    # Child can view tasks
    assert has_permission(ROLE_CHILD, "tasks:view") is True

    # Guest cannot create new tasks
    assert has_permission(ROLE_GUEST, "tasks:create") is False

    # Member, Admin, Owner can create and edit tasks
    assert has_permission(ROLE_MEMBER, "tasks:create") is True
    assert has_permission(ROLE_ADMIN, "tasks:create") is True
    assert has_permission(ROLE_OWNER, "tasks:create") is True
