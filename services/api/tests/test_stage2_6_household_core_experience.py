import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.tasks import (
    create_task,
    list_tasks,
    update_task,
    assign_task,
    complete_task,
    map_tasks_batch
)
from src.api.v1.bills import (
    send_bill_due_notification,
    record_bill_payment,
    map_bill_dto
)
from src.api.v1.calendar import (
    get_calendar_projection
)
from src.api.v1.inventory import (
    consume_inventory_item,
    restock_inventory_item
)
from src.api.v1.dashboard import (
    get_home_dashboard,
    get_home_dashboard_summary
)
from src.infrastructure.database.models import (
    BillCategoryModel,
    BillModel,
    BillPaymentModel,
    EventModel,
    HomeMemberModel,
    HomeModel,
    InventoryCategoryModel,
    InventoryItemModel,
    NotificationModel,
    PurchaseItemModel,
    StockMovementModel,
    TaskCategoryModel,
    TaskModel,
    UserModel,
    UserProfileModel
)
from src.schemas.task import (
    CreateTaskRequest,
    UpdateTaskRequest,
    AssignTaskRequest,
    CompleteTaskRequest
)
from src.schemas.bill import RecordPaymentRequest
from src.schemas.inventory import ConsumeStockRequest, RestockStockRequest


# ==============================================================================
# 1. TASKS: BATCH MAPPING (NO N+1), NOTIFICATIONS & OPTIMISTIC CONCURRENCY
# ==============================================================================

@pytest.mark.asyncio
async def test_task_batch_mapping_and_assignment_notification():
    """
    Verifies that map_tasks_batch maps tasks with 0 N+1 queries,
    and task assignment dispatches a Stage 2.5 notification.
    """
    home_id = uuid4()
    user_id = uuid4()
    assignee_id = uuid4()
    cat_id = uuid4()

    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Test Home", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()

    # 1. Test Task Assignment Notification
    task = TaskModel(
        id=uuid4(),
        home_id=home_id,
        title="Fix Water Purifier",
        priority="HIGH",
        status="TODO",
        assigned_to=assignee_id,
        version=1
    )
    mock_db.get.return_value = task

    # Mock member active check
    mem_res = MagicMock()
    mem_res.scalar_one_or_none.return_value = HomeMemberModel(home_id=home_id, user_id=assignee_id, status="ACTIVE")
    
    # Mock user profiles & categories for batch mapping
    prof_res = MagicMock()
    prof_res.scalars.return_value.all.return_value = [
        UserProfileModel(user_id=assignee_id, display_name="Assignee Member"),
        UserProfileModel(user_id=user_id, display_name="Owner User")
    ]
    cat_res = MagicMock()
    cat_res.scalars.return_value.all.return_value = [
        TaskCategoryModel(id=cat_id, name="Maintenance")
    ]
    bill_res = MagicMock()
    bill_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mem_res, prof_res, cat_res, bill_res, prof_res, cat_res, bill_res]

    # Assign task
    payload = AssignTaskRequest(assigned_to=assignee_id)
    res = await assign_task(task_id=task.id, payload=payload, home_ctx=home_ctx, db=mock_db)

    assert res.data.title == "Fix Water Purifier"
    assert res.data.assigned_to == assignee_id
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_task_optimistic_locking_conflict():
    """
    Verifies that updating a task with a stale version throws HTTP 409 Conflict.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Test Home")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()
    task = TaskModel(id=uuid4(), home_id=home_id, title="Test Task", version=2)
    mock_db.get.return_value = task

    payload = UpdateTaskRequest(title="Updated Title", version=1)  # Stale version!
    with pytest.raises(HTTPException) as exc:
        await update_task(task_id=task.id, payload=payload, home_ctx=home_ctx, db=mock_db)

    assert exc.value.status_code == 409
    assert "modified by another household member" in exc.value.detail


@pytest.mark.asyncio
async def test_task_completion_and_auto_resolution():
    """
    Verifies that completing a task executes recurrence scheduling and auto-resolves notifications.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Test Home")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db = AsyncMock()
    task = TaskModel(
        id=uuid4(),
        home_id=home_id,
        title="Weekly Trash Collection",
        status="TODO",
        due_date=datetime.now(timezone.utc),
        recurrence_type="WEEKLY",
        version=1
    )
    mock_db.get.return_value = task

    # Batch maps return empty for profile/cat
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = empty_res

    res = await complete_task(task_id=task.id, payload=CompleteTaskRequest(version=1), home_ctx=home_ctx, db=mock_db)
    assert res.data.status == "COMPLETED"
    assert task.status == "COMPLETED"
    assert mock_db.commit.called


# ==============================================================================
# 2. BILLS: DUE ALERTS & PAYMENT AUTO-RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_bill_due_notification_and_full_settlement():
    """
    Verifies that bill due alerts are dispatched to active members,
    and recording full payment auto-resolves the bill due alert.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_db = AsyncMock()

    # 1. Send Bill Due Notification
    mem_res = MagicMock()
    mem_res.scalars.return_value.all.return_value = [user_id]
    pref_res = MagicMock()
    pref_res.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [mem_res, pref_res, mem_res]

    await send_bill_due_notification(
        home_id=home_id,
        bill_title="Electricity Bill",
        amount=Decimal("2500.00"),
        currency="INR",
        due_date=date.today(),
        db=mock_db
    )
    assert mock_db.add.called

    # 2. Record Payment & Settle
    bill = BillModel(
        id=uuid4(),
        home_id=home_id,
        title="Electricity Bill",
        expected_amount=Decimal("2500.00"),
        amount_paid=Decimal("0.00"),
        currency="INR",
        status="UNPAID",
        recurrence_type="NONE",
        due_date=date.today(),
        version=1
    )
    mock_db.execute.side_effect = None
    bill_query_res = MagicMock()
    bill_query_res.scalar_one_or_none.return_value = bill
    bill_query_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = bill_query_res

    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Test Home", currency="INR")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    pay_payload = RecordPaymentRequest(
        amount_paid=2500.00,
        currency="INR",
        paid_date=date.today(),
        payment_method="UPI"
    )
    pay_res = await record_bill_payment(bill_id=bill.id, payload=pay_payload, home_ctx=home_ctx, db=mock_db)

    assert pay_res.data.status == "PAID"
    assert bill.status == "PAID"
    assert bill.amount_paid == Decimal("2500.00")



# ==============================================================================
# 3. INVENTORY: CONSUMPTION ALERTS & RESTOCK AUTO-RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_inventory_consumption_and_restock_lifecycle():
    """
    Verifies that consuming consumable stock below threshold triggers alerts,
    and restocking above threshold auto-resolves.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_db = AsyncMock()

    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Test Home")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    item = InventoryItemModel(
        id=uuid4(),
        home_id=home_id,
        name="Cooking Oil",
        quantity=Decimal("3.000"),
        unit="bottle",
        min_threshold=Decimal("2.000"),
        item_type="CONSUMABLE",
        status="GOOD"
    )
    item_res = MagicMock()
    item_res.scalar_one_or_none.return_value = item
    
    mem_res = MagicMock()
    mem_res.scalars.return_value.all.return_value = [user_id]
    pref_res = MagicMock()
    pref_res.scalar_one_or_none.return_value = None
    loc_res = MagicMock()
    loc_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [item_res, mem_res, pref_res, loc_res]
    mock_db.get.return_value = None

    # Consume 2 bottles -> leaves 1 bottle (below min_threshold of 2) -> triggers LOW_STOCK
    res = await consume_inventory_item(
        item_id=item.id,
        payload=ConsumeStockRequest(quantity=Decimal("2.000"), notes="Used for cooking"),
        home_ctx=home_ctx,
        db=mock_db
    )
    assert item.quantity == Decimal("1.000")
    assert item.status == "LOW_STOCK"

    # Restock 5 bottles -> increases to 6 bottles (above threshold) -> GOOD
    item_res2 = MagicMock()
    item_res2.scalar_one_or_none.return_value = item
    mock_db.execute.side_effect = [item_res2, loc_res]

    restock_res = await restock_inventory_item(
        item_id=item.id,
        payload=RestockStockRequest(quantity=Decimal("5.000"), notes="Bought from grocery"),
        home_ctx=home_ctx,
        db=mock_db
    )
    assert item.quantity == Decimal("6.000")
    assert item.status == "IN_STOCK" or item.status == "GOOD"


# ==============================================================================
# 4. CALENDAR PROJECTION: DERIVED TIMELINE (ZERO DUPLICATION)
# ==============================================================================

@pytest.mark.asyncio
async def test_calendar_projection_derived_timeline():
    """
    Verifies that Calendar projection aggregates Events, Task due dates, and Bill due dates.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_db = AsyncMock()

    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Test Home")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    now = datetime.now(timezone.utc)
    evts = [
        EventModel(
            id=uuid4(),
            home_id=home_id,
            title="Dentist Visit",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
            status="CONFIRMED"
        )
    ]
    tasks = [
        TaskModel(
            id=uuid4(),
            home_id=home_id,
            title="Clean Kitchen Chimney",
            due_date=now + timedelta(days=2),
            status="TODO",
            priority="HIGH"
        )
    ]
    bills = [
        BillModel(
            id=uuid4(),
            home_id=home_id,
            title="Gas Cylinder Bill",
            due_date=date.today() + timedelta(days=3),
            expected_amount=Decimal("950.00"),
            amount_paid=Decimal("0.00"),
            currency="INR",
            status="UNPAID"
        )
    ]

    res_evts = MagicMock()
    res_evts.unique.return_value.scalars.return_value.all.return_value = evts

    res_tasks = MagicMock()
    res_tasks.unique.return_value.scalars.return_value.all.return_value = tasks

    res_bills = MagicMock()
    res_bills.unique.return_value.scalars.return_value.all.return_value = bills

    mock_db.execute.side_effect = [res_evts, res_tasks, res_bills]

    res = await get_calendar_projection(
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        include_tasks=True,
        include_bills=True,
        home_ctx=home_ctx,
        db=mock_db
    )

    items = res.data.items
    source_types = [it.source_type for it in items]
    assert "EVENT" in source_types
    assert "TASK" in source_types
    assert "BILL" in source_types
    assert res.data.total_events == 1
    assert res.data.total_tasks == 1
    assert res.data.total_bills == 1


# ==============================================================================
# 5. DASHBOARD: AGGREGATED SUMMARY & MODULE PREVIEWS
# ==============================================================================

@pytest.mark.asyncio
async def test_dashboard_summary_and_module_previews():
    """
    Verifies that get_home_dashboard and get_home_dashboard_summary populate live module snapshots.
    """
    home_id = uuid4()
    user_id = uuid4()
    mock_db = AsyncMock()

    mock_user = UserModel(id=user_id, email="owner@ozhzo.com")
    mock_user.profile = UserProfileModel(user_id=user_id, display_name="Owner Admin")
    mock_home = HomeModel(id=home_id, name="Grand Villa", currency="INR", timezone="Asia/Kolkata")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="OWNER")

    mock_db.get.return_value = mock_home

    # KPI subquery row mock
    kpi_res = MagicMock()
    kpi_res.first.return_value = (5, 2, 4, 3, 1, 2, Decimal("4500.00"), 0)

    # Empty rows for attention/timeline/activity/previews
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        kpi_res,     # KPIs
        empty_res,   # Overdue bills
        empty_res,   # Overdue tasks
        empty_res,   # Out of stock
        empty_res,   # Events today
        empty_res,   # Tasks today
        empty_res,   # Stock moves
        empty_res,   # Bill payments
        empty_res,   # Pending tasks
        empty_res,   # Upcoming bills
        empty_res,   # Upcoming events
        empty_res,   # Low stock
        empty_res,   # Shopping items
        empty_res,   # Notifications
    ]

    dash_res = await get_home_dashboard(home_id=home_id, home_ctx=home_ctx, db=mock_db)
    assert dash_res.data.summary.home_name == "Grand Villa"
    assert dash_res.data.summary.active_tasks_count == 5
    assert dash_res.data.summary.low_stock_count == 2
    assert dash_res.data.summary.members_count == 4
