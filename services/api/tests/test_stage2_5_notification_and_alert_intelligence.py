import json
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.services.notification_service import NotificationService
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    NotificationModel,
    UserModel,
    UserProfileModel,
    UserNotificationPreferencesModel
)
from src.schemas.notification import (
    NotificationDTO,
    PriorityAlertSummaryDTO,
    PaginatedNotificationsResponse
)
from src.api.v1.notifications import (
    list_user_notifications,
    get_priority_alerts,
    mark_notification_read,
    acknowledge_notification,
    resolve_notification,
    dismiss_notification,
    mark_all_notifications_read
)


@pytest.mark.asyncio
async def test_priority_and_action_required_classification():
    service = NotificationService()
    mock_db = AsyncMock()
    user_id = uuid4()
    home_id = uuid4()

    pref = UserNotificationPreferencesModel(user_id=user_id, in_app_enabled=True)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = pref
    mock_db.execute.return_value = mock_res

    # 1. Critical payment failure auto-assigns requires_action=True
    await service.dispatch(
        home_id=home_id,
        user_id=user_id,
        title="Payment Failed",
        body="Payment of USD 49.00 failed.",
        type="PAYMENT_FAILED",
        priority="CRITICAL",
        action_type="RETRY_PAYMENT",
        action_url="/settings/subscription",
        action_label="Retry Payment",
        db=mock_db
    )

    added_obj = mock_db.add.call_args[0][0]
    assert isinstance(added_obj, NotificationModel)
    assert added_obj.priority == "CRITICAL"
    assert added_obj.requires_action is True
    assert added_obj.action_status == "OPEN"
    assert added_obj.action_type == "RETRY_PAYMENT"


@pytest.mark.asyncio
async def test_read_not_equals_resolved_invariant():
    """
    Mandatory Invariant: Reading a notification does NOT resolve an action-required notification.
    """
    mock_db = AsyncMock()
    user_id = uuid4()
    notif_id = uuid4()

    notif = NotificationModel(
        id=notif_id,
        user_id=user_id,
        title="Subscription Expiring Soon",
        body="Your subscription expires in 3 days.",
        type="SUBSCRIPTION_EXPIRING",
        priority="HIGH",
        requires_action=True,
        action_status="OPEN",
        action_type="RENEW",
        action_url="/settings/subscription",
        action_label="Renew Now",
        is_read=False
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = mock_res

    current_user = UserModel(id=user_id, email="user@ozhzo.com")

    # Step 1: User opens/reads the notification
    res = await mark_notification_read(notification_id=notif_id, current_user=current_user, db=mock_db)
    assert res.data.message == "Notification marked as read."

    # Verify: READ is True, but ACTION_STATUS is still OPEN and REQUIRES_ACTION is still True
    assert notif.is_read is True
    assert notif.read_at is not None
    assert notif.action_status == "OPEN"
    assert notif.requires_action is True
    assert notif.resolved_at is None

    # Step 2: User explicitly acknowledges
    await acknowledge_notification(notification_id=notif_id, current_user=current_user, db=mock_db)
    assert notif.action_status == "ACKNOWLEDGED"
    assert notif.resolved_at is None

    # Step 3: Underlying business action / explicit resolution resolves it
    await resolve_notification(notification_id=notif_id, current_user=current_user, db=mock_db)
    assert notif.action_status == "RESOLVED"
    assert notif.resolved_at is not None


@pytest.mark.asyncio
async def test_dismiss_action_required_notification():
    mock_db = AsyncMock()
    user_id = uuid4()
    notif_id = uuid4()

    notif = NotificationModel(
        id=notif_id,
        user_id=user_id,
        title="Home Invitation",
        body="Invited to Haven",
        type="HOME_INVITATION",
        priority="HIGH",
        requires_action=True,
        action_status="OPEN",
        is_read=False
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = mock_res

    current_user = UserModel(id=user_id, email="invitee@ozhzo.com")

    res = await dismiss_notification(notification_id=notif_id, current_user=current_user, db=mock_db)
    assert res.data.message == "Notification dismissed."
    assert notif.action_status == "DISMISSED"
    assert notif.dismissed_at is not None
    assert notif.is_read is True


@pytest.mark.asyncio
async def test_priority_alerts_endpoint_aggregation():
    mock_db = AsyncMock()
    user_id = uuid4()
    home_id = uuid4()

    notif1 = NotificationModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        title="Subscription Expired",
        body="Access expired. Renew now.",
        type="SUBSCRIPTION_EXPIRED",
        priority="CRITICAL",
        requires_action=True,
        action_status="OPEN",
        action_type="RENEW",
        action_url="/settings/subscription",
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )
    notif2 = NotificationModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        title="Invitation to join Villa",
        body="Invited by John.",
        type="HOME_INVITATION",
        priority="HIGH",
        requires_action=True,
        action_status="OPEN",
        action_type="JOIN_HOME",
        action_url="/invite/token-123",
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )

    # Mock DB query for items and count queries
    mock_items_res = MagicMock()
    mock_items_res.all.return_value = [(notif1, "Villa"), (notif2, "Villa")]

    mock_crit_count = MagicMock()
    mock_crit_count.scalar.return_value = 1

    mock_high_count = MagicMock()
    mock_high_count.scalar.return_value = 1

    mock_db.execute.side_effect = [mock_items_res, mock_crit_count, mock_high_count]

    current_user = UserModel(id=user_id, email="owner@ozhzo.com")
    resp = await get_priority_alerts(current_user=current_user, db=mock_db)

    assert resp.success is True
    data: PriorityAlertSummaryDTO = resp.data
    assert data.action_required_count == 2
    assert data.critical_count == 1
    assert data.high_count == 1
    assert len(data.items) == 2
    assert data.items[0].home_name == "Villa"
    assert data.items[0].priority == "CRITICAL"
    assert data.items[1].priority == "HIGH"


@pytest.mark.asyncio
async def test_stable_deduplication_engine():
    """
    Ensure identical event dispatches with stable dedup_key are suppressed and not duplicated.
    """
    service = NotificationService()
    mock_db = AsyncMock()
    user_id = uuid4()
    home_id = uuid4()

    pref = UserNotificationPreferencesModel(user_id=user_id, in_app_enabled=True)
    pref_res = MagicMock()
    pref_res.scalar_one_or_none.return_value = pref

    # 1. First dispatch: no existing record with dedup_key
    no_exist_res = MagicMock()
    no_exist_res.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [pref_res, no_exist_res]

    dedup = f"sub_expiring_sub123_3d_2026-09-04"
    res1 = await service.dispatch(
        home_id=home_id,
        user_id=user_id,
        title="Subscription Expiring Soon",
        body="Expires in 3 days.",
        type="SUBSCRIPTION_EXPIRING",
        priority="HIGH",
        dedup_key=dedup,
        db=mock_db
    )
    assert res1 is True
    assert mock_db.add.call_count == 1

    # 2. Second dispatch: duplicate dedup_key detected
    exist_res = MagicMock()
    exist_res.scalars.return_value.first.return_value = uuid4()
    mock_db.execute.side_effect = [pref_res, exist_res]

    res2 = await service.dispatch(
        home_id=home_id,
        user_id=user_id,
        title="Subscription Expiring Soon",
        body="Expires in 3 days.",
        type="SUBSCRIPTION_EXPIRING",
        priority="HIGH",
        dedup_key=dedup,
        db=mock_db
    )
    assert res2 is False
    # mock_db.add should not have been called a second time
    assert mock_db.add.call_count == 1


@pytest.mark.asyncio
async def test_auto_resolution_by_dedup_prefix():
    """
    Test resolving open action-required alerts when business event completes (e.g. invitation accepted).
    """
    service = NotificationService()
    mock_db = AsyncMock()

    mock_update_res = MagicMock()
    mock_update_res.rowcount = 2
    mock_db.execute.return_value = mock_update_res

    resolved_count = await service.resolve_by_dedup_prefix("inv_received_invite456", mock_db)
    assert resolved_count == 2
    assert mock_db.commit.call_count == 1
