import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.calendar import CreateEventRequest, UpdateEventRequest, UpdateParticipantStatusRequest
from src.api.v1.calendar import (
    create_event,
    update_event,
    rsvp_event,
    delete_event,
    send_event_invitations
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import EventModel, EventParticipantModel, UserModel, UserProfileModel


@pytest.mark.asyncio
async def test_create_event_with_participants_and_invitations():
    mock_db = AsyncMock()
    home_id = uuid4()
    creator_id = uuid4()
    participant_id = uuid4()

    creator_profile = UserProfileModel(user_id=creator_id, display_name="Alex")
    creator = UserModel(id=creator_id, email="alex@example.com", profile=creator_profile)
    ctx = HomeContext(home_id=home_id, user=creator, role=ROLE_OWNER)

    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=2)

    req = CreateEventRequest(
        title="Family Dinner & Game Night",
        description="Board games and homemade pizza",
        start_time=start,
        end_time=end,
        location="Dining Room",
        participant_user_ids=[participant_id]
    )

    mock_redis = AsyncMock()
    res = await create_event(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.title == "Family Dinner & Game Night"
    assert res.data.location == "Dining Room"
    # Added EventModel + 2 EventParticipantModel (creator + invited) + 1 NotificationModel
    assert mock_db.add.call_count >= 3


@pytest.mark.asyncio
async def test_rsvp_event():
    mock_db = AsyncMock()
    home_id = uuid4()
    event_id = uuid4()
    user_id = uuid4()

    part = EventParticipantModel(
        event_id=event_id,
        user_id=user_id,
        status="INVITED"
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = part
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="sarah@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_MEMBER)

    req = UpdateParticipantStatusRequest(status="ACCEPTED")
    res = await rsvp_event(event_id, req, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert part.status == "ACCEPTED"


def test_calendar_rbac_permissions():
    # All active roles (including Child and Guest) can view family calendar events
    assert has_permission(ROLE_CHILD, "events:view") is True
    assert has_permission(ROLE_GUEST, "events:view") is True

    # Guest and Child cannot create or delete events
    assert has_permission(ROLE_CHILD, "events:create") is False
    assert has_permission(ROLE_GUEST, "events:create") is False
    assert has_permission(ROLE_GUEST, "events:delete") is False

    # Owner, Admin, Member have full calendar rights
    assert has_permission(ROLE_OWNER, "events:create") is True
    assert has_permission(ROLE_ADMIN, "events:edit") is True
    assert has_permission(ROLE_MEMBER, "events:create") is True
