import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.calendar import CreateEventRequest, UpdateEventRequest
from src.api.v1.calendar import (
    create_event,
    update_event,
    get_event,
    delete_event,
    list_home_events
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import (
    EventModel,
    EventCategoryModel,
    UserModel,
    UserProfileModel
)


@pytest.mark.asyncio
async def test_create_event_with_category_name_autoresolution():
    """
    1. Authenticated user can create calendar event.
    2. Event is saved to correct Home.
    3. Category name is auto-resolved or provisioned.
    """
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="alex@example.com")
    user.profile = UserProfileModel(user_id=user_id, display_name="Alex Rivera")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)

    req = CreateEventRequest(
        title="Family Doctor Appointment",
        description="Annual checkup with Dr. Smith",
        start_time=start,
        end_time=end,
        is_all_day=False,
        location="City Medical Center",
        category_name="Doctor / Health",
        recurrence_type="NONE"
    )

    # Mock DB query for category lookup returning None (triggers new category creation)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    res = await create_event(payload=req, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert res.data.title == "Family Doctor Appointment"
    assert res.data.location == "City Medical Center"
    assert res.data.start_time == start
    assert res.data.end_time == end
    assert res.data.home_id == home_id
    assert res.data.created_by == user_id
    assert mock_db.add.call_count >= 2  # EventCategory + EventModel


@pytest.mark.asyncio
async def test_create_event_with_recurrence_and_all_day():
    """
    Test recurring household schedule creation (e.g. Weekly Garbage collection, Monthly Rent).
    """
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="alex@example.com")
    user.profile = UserProfileModel(user_id=user_id, display_name="Alex Rivera")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    start = datetime(2026, 8, 20, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 20, 23, 59, 59, tzinfo=timezone.utc)

    req = CreateEventRequest(
        title="Garbage Collection & Recycling",
        description="Every week recycling bin pickup",
        start_time=start,
        end_time=end,
        is_all_day=True,
        location="Front Curb",
        category_name="Maintenance",
        recurrence_type="WEEKLY",
        recurrence_interval_days=7
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    res = await create_event(payload=req, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert res.data.title == "Garbage Collection & Recycling"
    assert res.data.is_all_day is True
    assert res.data.recurrence_type == "WEEKLY"
    assert res.data.recurrence_interval_days == 7


@pytest.mark.asyncio
async def test_invalid_date_or_payload_rejected():
    """
    Invalid end time before start time should fail schema validation.
    """
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start - timedelta(hours=1)

    with pytest.raises(ValidationError):
        CreateEventRequest(
            title="Impossible Event",
            start_time=start,
            end_time=end
        )


@pytest.mark.asyncio
async def test_get_event_preserves_timestamp_and_timezone():
    """
    Event retrieval must preserve exact UTC timestamp without offset distortion.
    """
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()

    exact_time = datetime(2026, 8, 18, 13, 30, 0, tzinfo=timezone.utc)
    event = EventModel(
        id=event_id,
        home_id=home_id,
        title="Birthday Outing",
        location="Green Park",
        start_time=exact_time,
        end_time=exact_time + timedelta(hours=3),
        is_all_day=False,
        status="CONFIRMED",
        version=1,
        created_by=user_id,
        created_at=exact_time,
        updated_at=exact_time,
        participants=[]
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = event
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    user.profile = UserProfileModel(user_id=user_id, display_name="Alex Rivera")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_MEMBER)

    res = await get_event(event_id=event_id, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert res.data.id == event_id
    assert res.data.start_time == exact_time
    assert res.data.start_time.hour == 13
    assert res.data.start_time.minute == 30


@pytest.mark.asyncio
async def test_update_event_and_delete():
    """
    Test updating an existing event's title, location, category and then deleting it.
    """
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()

    now = datetime.now(timezone.utc)
    event = EventModel(
        id=event_id,
        home_id=home_id,
        title="School Meeting",
        location="Auditorium",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=2, hours=1),
        is_all_day=False,
        status="CONFIRMED",
        version=1,
        created_by=user_id,
        created_at=now,
        updated_at=now,
        participants=[]
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = event
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    user.profile = UserProfileModel(user_id=user_id, display_name="Alex Rivera")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    # 1. Update event
    update_req = UpdateEventRequest(
        title="School Parent-Teacher Conference",
        location="Room 204",
        version=1
    )
    update_res = await update_event(event_id=event_id, payload=update_req, home_ctx=ctx, db=mock_db)

    assert update_res.success is True
    assert event.title == "School Parent-Teacher Conference"
    assert event.location == "Room 204"
    assert event.version == 2

    # 2. Delete event
    delete_res = await delete_event(event_id=event_id, home_ctx=ctx, db=mock_db)
    assert delete_res.success is True
    assert event.status == "CANCELLED"
    assert event.deleted_at is not None


@pytest.mark.asyncio
async def test_cross_home_event_access_prevented():
    """
    Accessing or modifying an event in another home must return 404.
    """
    mock_db = AsyncMock()
    home_a = uuid4()
    home_b = uuid4()
    event_id = uuid4()
    user_id = uuid4()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    ctx_b = HomeContext(home_id=home_b, user=user, role=ROLE_MEMBER)

    with pytest.raises(HTTPException) as exc_info:
        await get_event(event_id=event_id, home_ctx=ctx_b, db=mock_db)
    assert exc_info.value.status_code == 404


def test_calendar_permissions():
    """
    Verify RBAC permissions for calendar operations across all household roles.
    """
    assert has_permission(ROLE_OWNER, "calendar:view") is True
    assert has_permission(ROLE_OWNER, "calendar:create") is True
    assert has_permission(ROLE_OWNER, "calendar:edit") is True
    assert has_permission(ROLE_OWNER, "calendar:delete") is True

    assert has_permission(ROLE_ADMIN, "calendar:view") is True
    assert has_permission(ROLE_ADMIN, "calendar:create") is True
    assert has_permission(ROLE_ADMIN, "calendar:edit") is True
    assert has_permission(ROLE_ADMIN, "calendar:delete") is True

    assert has_permission(ROLE_MEMBER, "calendar:view") is True
    assert has_permission(ROLE_MEMBER, "calendar:create") is True
    assert has_permission(ROLE_MEMBER, "calendar:edit") is True
    assert has_permission(ROLE_MEMBER, "calendar:delete") is False

    assert has_permission(ROLE_CHILD, "calendar:view") is True
    assert has_permission(ROLE_CHILD, "calendar:create") is False
    assert has_permission(ROLE_CHILD, "calendar:delete") is False

    assert has_permission(ROLE_GUEST, "calendar:view") is True
    assert has_permission(ROLE_GUEST, "calendar:create") is False


@pytest.mark.asyncio
async def test_calendar_projection_retrieval_and_both_keys():
    """
    Verify get_calendar_projection returns both `items` and `timeline_items` with full event metadata.
    """
    from src.api.v1.calendar import get_calendar_projection

    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()

    now = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    event = EventModel(
        id=event_id,
        home_id=home_id,
        title="Annual Pediatric Checkup",
        location="Children's Hospital",
        description="Routine pediatric visit",
        start_time=now,
        end_time=now + timedelta(hours=1),
        is_all_day=False,
        status="CONFIRMED",
        version=1,
        created_by=user_id,
        created_at=now,
        updated_at=now,
        participants=[]
    )

    # Mock execute return for events query
    mock_res_events = MagicMock()
    mock_res_events.unique.return_value.scalars.return_value.all.return_value = [event]

    # Mock execute return for tasks and bills queries
    mock_res_empty = MagicMock()
    mock_res_empty.unique.return_value.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mock_res_events, mock_res_empty, mock_res_empty]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await get_calendar_projection(
        start_date=now - timedelta(days=7),
        end_date=now + timedelta(days=7),
        include_tasks=True,
        include_bills=True,
        home_ctx=ctx,
        db=mock_db
    )

    assert res.success is True
    assert res.data.total_events == 1
    assert len(res.data.items) == 1
    assert res.data.timeline_items is not None
    assert len(res.data.timeline_items) == 1

    item = res.data.items[0]
    assert item.source_type == "EVENT"
    assert item.source_id == event_id
    assert item.title == "Annual Pediatric Checkup"
    assert item.start == now
    assert item.location == "Children's Hospital"


@pytest.mark.asyncio
async def test_calendar_timezone_coverage_across_day():
    """
    Verify events at 00:00, 01:00, 12:00, 23:00 on the same date are normalized to UTC timezone-aware.
    """
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    hours = [0, 1, 12, 23]
    for h in hours:
        # Naive datetime simulation
        start_naive = datetime(2026, 9, 2, h, 0, 0)
        end_naive = datetime(2026, 9, 2, h, 45, 0)

        req = CreateEventRequest(
            title=f"Schedule block at hour {h:02d}",
            start_time=start_naive,
            end_time=end_naive,
            is_all_day=False,
            category_name="Family"
        )

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        res = await create_event(payload=req, home_ctx=ctx, db=mock_db)
        assert res.success is True
        assert res.data.start_time.tzinfo is not None
        assert res.data.start_time.hour == h
        assert res.data.start_time.day == 2


@pytest.mark.asyncio
async def test_multi_home_isolation_in_projection():
    """
    Events belonging to Home A must not be visible in Home B projection.
    """
    from src.api.v1.calendar import get_calendar_projection

    mock_db = AsyncMock()
    home_a = uuid4()
    home_b = uuid4()
    user_id = uuid4()

    now = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    # DB returns empty list when queried for Home B
    mock_res_empty = MagicMock()
    mock_res_empty.unique.return_value.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res_empty

    user = UserModel(id=user_id, email="alex@example.com")
    ctx_b = HomeContext(home_id=home_b, user=user, role=ROLE_OWNER)

    res = await get_calendar_projection(
        start_date=now - timedelta(days=7),
        end_date=now + timedelta(days=7),
        include_tasks=False,
        include_bills=False,
        home_ctx=ctx_b,
        db=mock_db
    )

    assert res.success is True
    assert res.data.total_events == 0
    assert len(res.data.items) == 0

