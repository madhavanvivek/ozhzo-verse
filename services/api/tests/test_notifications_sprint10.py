import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.services.notification_service import NotificationService, InAppChannelHandler
from src.infrastructure.database.models import (
    NotificationModel,
    UserModel,
    UserNotificationPreferencesModel
)
from src.schemas.notification import UpdateNotificationPreferencesRequest
from src.api.v1.notifications import (
    list_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    get_preferences,
    update_preferences
)


@pytest.mark.asyncio
async def test_notification_service_dispatch():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    # User preferences with all enabled
    pref = UserNotificationPreferencesModel(user_id=user_id, in_app_enabled=True, low_stock_enabled=True)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = pref
    mock_db.execute.return_value = mock_res

    service = NotificationService()
    mock_redis = AsyncMock()

    dispatched = await service.dispatch(
        home_id=home_id,
        user_id=user_id,
        title="Low Stock: Flour",
        body="Flour has 0.5 kg remaining.",
        type="LOW_STOCK",
        db=mock_db,
        redis_client=mock_redis
    )

    assert dispatched is True
    assert mock_db.add.call_count >= 1


@pytest.mark.asyncio
async def test_notification_suppression_by_preference():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    # User disabled low_stock notifications
    pref = UserNotificationPreferencesModel(
        user_id=user_id,
        in_app_enabled=True,
        low_stock_enabled=False
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = pref
    mock_db.execute.return_value = mock_res

    service = NotificationService()
    mock_redis = AsyncMock()

    dispatched = await service.dispatch(
        home_id=home_id,
        user_id=user_id,
        title="Low Stock: Salt",
        body="Salt is out of stock.",
        type="LOW_STOCK",
        db=mock_db,
        redis_client=mock_redis
    )

    # Suppressed by user preference
    assert dispatched is False
    assert mock_db.add.call_count == 0


@pytest.mark.asyncio
async def test_mark_as_read_and_mark_all_read():
    mock_db = AsyncMock()
    user_id = uuid4()
    notif_id = uuid4()

    notif = NotificationModel(
        id=notif_id,
        user_id=user_id,
        title="Chore assigned",
        body="Mop floor",
        type="TASK_ASSIGNED",
        is_read=False
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = mock_res

    service = NotificationService()

    # 1. Single mark as read
    res = await service.mark_as_read(notif_id, user_id, mock_db)
    assert res is True
    assert notif.is_read is True
    assert notif.read_at is not None

    # 2. Mark all as read
    mock_update_res = MagicMock()
    mock_update_res.rowcount = 5
    mock_db.execute.return_value = mock_update_res

    count = await service.mark_all_as_read(user_id, mock_db)
    assert count == 5


def test_notification_all_types():
    valid_types = [
        "TASK_ASSIGNED",
        "BILL_REMINDER",
        "LOW_STOCK",
        "EVENT_REMINDER",
        "HOME_INVITATION",
        "SYSTEM"
    ]
    service = NotificationService()
    pref = UserNotificationPreferencesModel(user_id=uuid4())

    for t in valid_types:
        assert service.is_type_enabled(t, pref) is True
