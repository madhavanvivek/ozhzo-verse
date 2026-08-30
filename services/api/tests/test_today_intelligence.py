import pytest
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
import zoneinfo
from decimal import Decimal

from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER
from src.api.dependencies import HomeContext
from src.api.v1.today import get_unified_today_view, resolve_home_timezone
from src.infrastructure.database.models import (
    BillModel,
    EventModel,
    HomeModel,
    HomeMemberModel,
    InventoryItemModel,
    InvitationModel,
    NotificationModel,
    PurchaseItemModel,
    TaskModel,
    UserModel,
    UserProfileModel
)


@pytest.mark.asyncio
async def test_01_empty_home_baseline():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Empty Haven", timezone="UTC", currency="USD")
    user = UserModel(id=user_id, email="test@example.com")
    user.profile = UserProfileModel(user_id=user_id, display_name="Test User")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    mock_db.get.return_value = home

    mock_scalars = MagicMock()
    mock_scalars.scalars.return_value.all.return_value = []
    mock_scalars.scalar.return_value = 0
    mock_db.execute.return_value = mock_scalars

    res = await get_unified_today_view(home_ctx=ctx, db=mock_db)
    data = res.data

    assert data.home_id == home_id
    assert data.home_name == "Empty Haven"
    assert data.summary.total_items == 0
    assert data.summary.critical_count == 0
    assert data.summary.high_count == 0
    assert len(data.needs_attention) == 0
    assert len(data.timeline) == 0


@pytest.mark.asyncio
async def test_02_tasks_due_today_and_overdue():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()

    home = HomeModel(id=home_id, name="Active Home", timezone="UTC", currency="USD")
    user = UserModel(id=user_id, email="me@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_db.get.return_value = home

    tz_info, _ = resolve_home_timezone("UTC")
    today = datetime.now(tz_info).date()

    overdue_task = TaskModel(
        id=uuid4(),
        home_id=home_id,
        title="Fix Leaking Pipe",
        priority="URGENT",
        status="TODO",
        due_date=today - timedelta(days=2),
        assigned_to=user_id
    )
    due_today_task = TaskModel(
        id=uuid4(),
        home_id=home_id,
        title="Water Plants",
        priority="NORMAL",
        status="TODO",
        due_date=today,
        assigned_to=other_user_id
    )

    def mock_execute(query):
        res = MagicMock()
        query_str = str(query)
        if "tasks" in query_str and "count" not in query_str:
            res.scalars.return_value.all.return_value = [overdue_task, due_today_task]
        elif "home_members" in query_str:
            res.scalars.return_value.all.return_value = []
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar.return_value = 0
        return res

    mock_db.execute.side_effect = mock_execute

    res = await get_unified_today_view(home_ctx=ctx, db=mock_db)
    data = res.data

    assert len(data.tasks.overdue) == 1
    assert data.tasks.overdue[0].title == "Fix Leaking Pipe"
    assert data.tasks.overdue[0].priority == "CRITICAL"
    assert "Overdue (2d)" in data.tasks.overdue[0].badge_text

    assert len(data.tasks.due_today) == 1
    assert data.tasks.due_today[0].title == "Water Plants"
    assert data.tasks.due_today[0].priority == "HIGH"

    assert len(data.tasks.my_tasks) == 1
    assert data.tasks.my_tasks[0].title == "Fix Leaking Pipe"
    assert len(data.tasks.family_tasks) == 1
    assert data.tasks.family_tasks[0].title == "Water Plants"


@pytest.mark.asyncio
async def test_03_bills_due_today_and_overdue():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Bill Haven", timezone="UTC", currency="EUR")
    user = UserModel(id=user_id, email="bill@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_db.get.return_value = home

    tz_info, _ = resolve_home_timezone("UTC")
    today = datetime.now(tz_info).date()

    overdue_bill = BillModel(
        id=uuid4(),
        home_id=home_id,
        title="Electricity Bill",
        expected_amount=120.0,
        amount_paid=0.0,
        currency="EUR",
        due_date=today - timedelta(days=3),
        status="UNPAID"
    )
    due_today_bill = BillModel(
        id=uuid4(),
        home_id=home_id,
        title="Internet Subscription",
        expected_amount=50.0,
        amount_paid=0.0,
        currency="EUR",
        due_date=today,
        status="UNPAID"
    )

    def mock_execute(query):
        res = MagicMock()
        query_str = str(query)
        if "bills" in query_str:
            res.scalars.return_value.all.return_value = [overdue_bill, due_today_bill]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar.return_value = 0
        return res

    mock_db.execute.side_effect = mock_execute

    res = await get_unified_today_view(home_ctx=ctx, db=mock_db)
    data = res.data

    assert len(data.bills.overdue) == 1
    assert data.bills.overdue[0].priority == "CRITICAL"
    assert "Overdue (3d)" in data.bills.overdue[0].badge_text
    assert len(data.bills.due_today) == 1
    assert data.bills.due_today[0].priority == "HIGH"
    assert data.bills.total_due_today_amount == 50.0


@pytest.mark.asyncio
async def test_04_inventory_and_shopping_alerts():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Pantry Home", timezone="UTC", currency="USD")
    user = UserModel(id=user_id, email="pantry@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_db.get.return_value = home

    out_stock = InventoryItemModel(
        id=uuid4(),
        home_id=home_id,
        name="Milk 1 Gallon",
        quantity=0,
        unit="gal",
        item_type="CONSUMABLE"
    )
    low_stock = InventoryItemModel(
        id=uuid4(),
        home_id=home_id,
        name="Eggs Large",
        quantity=2,
        min_threshold=6,
        unit="count",
        item_type="CONSUMABLE"
    )
    pending_purchase = PurchaseItemModel(
        id=uuid4(),
        home_id=home_id,
        name="Dish Soap",
        quantity=Decimal("1.000"),
        unit="bottle",
        status="PENDING"
    )

    def mock_execute(query):
        res = MagicMock()
        query_str = str(query)
        if "inventory_items" in query_str:
            res.scalars.return_value.all.return_value = [out_stock, low_stock]
        elif "purchase_items" in query_str:
            res.scalars.return_value.all.return_value = [pending_purchase]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar.return_value = 0
        return res

    mock_db.execute.side_effect = mock_execute

    res = await get_unified_today_view(home_ctx=ctx, db=mock_db)
    data = res.data

    assert len(data.inventory.out_of_stock) == 1
    assert data.inventory.out_of_stock[0].priority == "CRITICAL"
    assert len(data.inventory.low_stock) == 1
    assert data.inventory.low_stock[0].priority == "HIGH"
    assert len(data.shopping.pending_items) == 1
    assert data.shopping.pending_items[0].title == "Dish Soap"


@pytest.mark.asyncio
async def test_05_calendar_events_and_projection():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Calendar Home", timezone="UTC", currency="USD")
    user = UserModel(id=user_id, email="cal@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_db.get.return_value = home

    now_utc = datetime.now(timezone.utc)
    today_event = EventModel(
        id=uuid4(),
        home_id=home_id,
        title="Team Standup",
        start_time=now_utc,
        end_time=now_utc + timedelta(hours=1),
        is_all_day=False,
        status="CONFIRMED",
        created_by=user_id
    )
    upcoming_event = EventModel(
        id=uuid4(),
        home_id=home_id,
        title="Weekend BBQ",
        start_time=now_utc + timedelta(days=3),
        end_time=now_utc + timedelta(days=3, hours=2),
        is_all_day=False,
        status="CONFIRMED",
        created_by=user_id
    )

    def mock_execute(query):
        res = MagicMock()
        query_str = str(query)
        if "events" in query_str:
            res.scalars.return_value.all.return_value = [today_event, upcoming_event]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar.return_value = 0
        return res

    mock_db.execute.side_effect = mock_execute

    res = await get_unified_today_view(home_ctx=ctx, db=mock_db)
    data = res.data

    assert len(data.calendar.today_events) == 1
    assert data.calendar.today_events[0].title == "Team Standup"
    assert len(data.calendar.upcoming_events) == 1
    assert data.calendar.upcoming_events[0].title == "Weekend BBQ"


@pytest.mark.asyncio
async def test_06_family_workload_and_notifications():
    mock_db = AsyncMock()
    home_id = uuid4()
    user1_id = uuid4()
    user2_id = uuid4()

    home = HomeModel(id=home_id, name="Family Home", timezone="UTC", currency="USD")
    user1 = UserModel(id=user1_id, email="parent@example.com")
    user1.profile = UserProfileModel(user_id=user1_id, display_name="Parent")
    ctx = HomeContext(home_id=home_id, user=user1, role=ROLE_OWNER)
    mock_db.get.return_value = home

    user2 = UserModel(id=user2_id, email="kid@example.com")
    user2.profile = UserProfileModel(user_id=user2_id, display_name="Kid")

    member1 = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=user1_id, role="OWNER", status="ACTIVE")
    member1.user = user1
    member2 = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=user2_id, role="MEMBER", status="ACTIVE")
    member2.user = user2

    notif = NotificationModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user1_id,
        title="Task Reminder",
        body="Please finish cleaning",
        type="TASK_REMINDER",
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )

    def mock_execute(query):
        res = MagicMock()
        query_str = str(query)
        if "home_members" in query_str:
            res.scalars.return_value.all.return_value = [member1, member2]
        elif "notifications" in query_str:
            res.scalars.return_value.all.return_value = [notif]
        elif "invitations" in query_str:
            res.scalar.return_value = 1
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar.return_value = 0
        return res

    mock_db.execute.side_effect = mock_execute

    res = await get_unified_today_view(home_ctx=ctx, db=mock_db)
    data = res.data

    assert data.family.active_members_count == 2
    assert data.family.pending_invitations_count == 1
    assert len(data.family.member_workloads) == 2
    assert data.notifications.unread_count == 1
    assert data.notifications.important_alerts[0].title == "Task Reminder"


@pytest.mark.asyncio
async def test_07_timezone_resolution():
    tz1, str1 = resolve_home_timezone("America/New_York")
    assert str1 == "America/New_York"
    assert isinstance(tz1, zoneinfo.ZoneInfo)

    tz2, str2 = resolve_home_timezone("Invalid/Timezone")
    assert str2 == "UTC"
    assert isinstance(tz2, zoneinfo.ZoneInfo)

    tz3, str3 = resolve_home_timezone(None)
    assert str3 == "UTC"
