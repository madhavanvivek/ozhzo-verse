import pytest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.domain.permissions import ROLE_OWNER, ROLE_MEMBER
from src.schemas.calendar import TimelineItemDTO, CalendarProjectionResponse
from src.api.v1.calendar import get_calendar_projection
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import (
    EventModel,
    TaskModel,
    BillModel,
    InventoryItemModel,
    UserModel,
    UserProfileModel
)


@pytest.mark.asyncio
async def test_calendar_projection_includes_events_tasks_and_unpaid_bills():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()
    task_id = uuid4()
    bill_id = uuid4()

    now = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)
    target_date = date(2026, 9, 12)

    # 1. Mock Event
    event = EventModel(
        id=event_id,
        home_id=home_id,
        title="Doctor Appointment",
        location="City Clinic",
        start_time=now,
        end_time=now + timedelta(hours=1),
        is_all_day=False,
        status="CONFIRMED",
        version=1,
        created_by=user_id,
        participants=[]
    )

    # 2. Mock Active Task
    task = TaskModel(
        id=task_id,
        home_id=home_id,
        title="Pay school fee",
        due_date=target_date,
        status="PENDING",
        priority="HIGH"
    )

    # 3. Mock Unpaid Bill
    bill = BillModel(
        id=bill_id,
        home_id=home_id,
        title="Electricity Bill",
        expected_amount=Decimal("2400.00"),
        amount_paid=Decimal("0.00"),
        currency="INR",
        due_date=target_date,
        status="UNPAID",
        recurrence_type="NONE"
    )

    # Mocks for 4 sequential queries: events, tasks, bills, inventory
    res_events = MagicMock()
    res_events.unique.return_value.scalars.return_value.all.return_value = [event]

    res_tasks = MagicMock()
    res_tasks.unique.return_value.scalars.return_value.all.return_value = [task]

    res_bills = MagicMock()
    res_bills.unique.return_value.scalars.return_value.all.return_value = [bill]

    res_inv = MagicMock()
    res_inv.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [res_events, res_tasks, res_bills, res_inv]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await get_calendar_projection(
        start_date=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
        include_tasks=True,
        include_bills=True,
        home_ctx=ctx,
        db=mock_db
    )

    assert res.success is True
    data = res.data
    assert data.total_events == 1
    assert data.total_tasks == 1
    assert data.total_bills == 1
    assert len(data.items) == 3

    # Check Event item
    evt_item = next(i for i in data.items if i.source_type == "EVENT")
    assert evt_item.title == "Doctor Appointment"
    assert evt_item.source_id == event_id
    assert evt_item.editable is True
    assert evt_item.status == "CONFIRMED"

    # Check Task item
    task_item = next(i for i in data.items if i.source_type == "TASK")
    assert "Pay school fee" in task_item.title
    assert task_item.source_id == task_id
    assert task_item.editable is False
    assert task_item.status == "PENDING"
    assert task_item.navigation_target == f"/tasks/{task_id}"

    # Check Bill item
    bill_item = next(i for i in data.items if i.source_type == "BILL")
    assert "Electricity Bill" in bill_item.title
    assert "2400.00" in bill_item.title
    assert bill_item.source_id == bill_id
    assert bill_item.status == "UNPAID"
    assert bill_item.navigation_target == f"/bills/{bill_id}"


@pytest.mark.asyncio
async def test_calendar_projection_includes_paid_bills_and_recurring_cycle():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    paid_oneoff_id = uuid4()
    paid_recurring_id = uuid4()

    due_1 = date(2026, 9, 5)
    due_2 = date(2026, 9, 8)

    # 1. One-off Paid Bill (₹650 Water / Sewage Cleaning)
    oneoff_paid_bill = BillModel(
        id=paid_oneoff_id,
        home_id=home_id,
        title="Water / Sewage Cleaning",
        expected_amount=Decimal("650.00"),
        amount_paid=Decimal("650.00"),
        currency="INR",
        due_date=due_1,
        status="PAID",
        recurrence_type="NONE"
    )

    # 2. Recurring Paid Bill (Monthly Fiber Internet)
    recurring_paid_bill = BillModel(
        id=paid_recurring_id,
        home_id=home_id,
        title="Fiber Internet",
        expected_amount=Decimal("999.00"),
        amount_paid=Decimal("999.00"),
        currency="INR",
        due_date=due_2,
        status="PAID",
        recurrence_type="MONTHLY"
    )

    res_events = MagicMock()
    res_events.unique.return_value.scalars.return_value.all.return_value = []

    res_tasks = MagicMock()
    res_tasks.unique.return_value.scalars.return_value.all.return_value = []

    res_bills = MagicMock()
    res_bills.unique.return_value.scalars.return_value.all.return_value = [oneoff_paid_bill, recurring_paid_bill]

    res_inv = MagicMock()
    res_inv.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [res_events, res_tasks, res_bills, res_inv]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await get_calendar_projection(
        start_date=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 10, 15, 23, 59, 59, tzinfo=timezone.utc),
        include_tasks=True,
        include_bills=True,
        home_ctx=ctx,
        db=mock_db
    )

    assert res.success is True
    items = res.data.items

    # 1. One-off bill appears once as PAID
    oneoff_items = [i for i in items if i.source_id == paid_oneoff_id]
    assert len(oneoff_items) == 1
    assert oneoff_items[0].status == "PAID"
    assert "(Paid)" in oneoff_items[0].title
    assert "650.00" in oneoff_items[0].title

    # 2. Recurring bill appears as PAID for current cycle, and UPCOMING for next cycle (+1 month = Oct 8)
    rec_items = [i for i in items if i.source_id == paid_recurring_id]
    assert len(rec_items) == 2

    paid_cycle = next(i for i in rec_items if i.status == "PAID")
    assert "(Paid)" in paid_cycle.title
    assert paid_cycle.start.date() == due_2

    upcoming_cycle = next(i for i in rec_items if i.status == "UPCOMING")
    assert "(Upcoming)" in upcoming_cycle.title
    assert upcoming_cycle.start.date() == date(2026, 10, 8)


@pytest.mark.asyncio
async def test_calendar_projection_completed_tasks_and_inventory_service():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()
    task_id = uuid4()
    inv_id = uuid4()

    task_date = date(2026, 9, 15)
    service_date = date(2026, 9, 18)

    # 1. Completed Task
    task = TaskModel(
        id=task_id,
        home_id=home_id,
        title="Replace AC Filter",
        due_date=task_date,
        status="COMPLETED",
        priority="NORMAL"
    )

    # 2. Inventory Item with next_service_due_at
    inv_item = InventoryItemModel(
        id=inv_id,
        home_id=home_id,
        name="Master Bedroom AC",
        next_service_due_at=service_date
    )

    res_events = MagicMock()
    res_events.unique.return_value.scalars.return_value.all.return_value = []

    res_tasks = MagicMock()
    res_tasks.unique.return_value.scalars.return_value.all.return_value = [task]

    res_bills = MagicMock()
    res_bills.unique.return_value.scalars.return_value.all.return_value = []

    res_inv = MagicMock()
    res_inv.scalars.return_value.all.return_value = [inv_item]

    mock_db.execute.side_effect = [res_events, res_tasks, res_bills, res_inv]

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    res = await get_calendar_projection(
        start_date=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
        include_tasks=True,
        include_bills=True,
        home_ctx=ctx,
        db=mock_db
    )

    assert res.success is True
    items = res.data.items

    # Task item verification
    task_proj = next(i for i in items if i.source_type == "TASK")
    assert task_proj.status == "COMPLETED"
    assert task_proj.meta_info["is_completed"] is True

    # Inventory item verification
    inv_proj = next(i for i in items if i.source_type == "INVENTORY")
    assert inv_proj.source_id == inv_id
    assert inv_proj.title == "Maintenance: Master Bedroom AC Service Due"
    assert inv_proj.status == "DUE"
    assert inv_proj.navigation_target == "/inventory"
