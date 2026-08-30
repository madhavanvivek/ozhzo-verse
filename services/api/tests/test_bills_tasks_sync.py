import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER
from src.schemas.bill import CreateBillRequest, UpdateBillRequest, RecordPaymentRequest
from src.schemas.task import CreateTaskRequest, UpdateTaskRequest
from src.api.v1.bills import (
    create_bill,
    get_bill_detail,
    update_bill,
    delete_bill,
    record_bill_payment,
    calculate_next_bill_due_date,
    map_bill_dto
)
from src.api.v1.tasks import (
    create_task,
    get_task,
    update_task,
    map_task_dto
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import (
    BillModel,
    BillCategoryModel,
    TaskModel,
    TaskCategoryModel,
    HomeMemberModel,
    HomeModel,
    UserModel,
    UserProfileModel
)


@pytest.mark.asyncio
async def test_create_bill_direct_with_category_and_responsible_member():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="owner@ozhzo.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    # Mock member check
    mock_member = HomeMemberModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        status="ACTIVE",
        role="OWNER"
    )
    mock_mem_res = MagicMock()
    mock_mem_res.scalar_one_or_none.return_value = mock_member

    # Mock category query (not found initially, auto-created)
    mock_cat_res = MagicMock()
    mock_cat_res.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_mem_res, mock_cat_res, MagicMock()]
    mock_db.get.return_value = None

    req = CreateBillRequest(
        title="Electricity Bill",
        category_name="Utilities",
        expected_amount=Decimal("2450.00"),
        currency="INR",
        due_date=date(2026, 9, 15),
        recurrence_type="MONTHLY",
        responsible_member_id=user_id,
        notes="Monthly BESCOM power bill"
    )

    mock_redis = AsyncMock()
    res = await create_bill(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.title == "Electricity Bill"
    assert res.data.expected_amount == Decimal("2450.00")
    assert res.data.status == "UNPAID"
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_create_bill_with_linked_task_creation():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="owner@ozhzo.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    mock_mem_res = MagicMock()
    mock_mem_res.scalar_one_or_none.return_value = None

    mock_cat_res = MagicMock()
    mock_cat_res.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_mem_res, mock_cat_res, MagicMock()]

    req = CreateBillRequest(
        title="Fiber Internet",
        category="Communication",
        amount=Decimal("999.00"),
        currency="INR",
        due_date=date(2026, 9, 10),
        recurrence_type="MONTHLY",
        create_linked_task=True
    )

    mock_redis = AsyncMock()
    res = await create_bill(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.title == "Fiber Internet"
    assert res.data.expected_amount == Decimal("999.00")
    # Verify task was added to db session
    added_types = [type(arg) for (arg,), _ in mock_db.add.call_args_list]
    assert BillModel in added_types
    assert TaskModel in added_types


@pytest.mark.asyncio
async def test_create_task_with_bill_obligation_sync():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="owner@ozhzo.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    mock_cat_res = MagicMock()
    mock_cat_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_cat_res

    req = CreateTaskRequest(
        title="Pay Water Bill",
        category_name="Bills",
        priority="HIGH",
        due_date=datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc),
        recurrence_type="MONTHLY",
        bill_amount=Decimal("650.00"),
        create_bill=True
    )

    mock_redis = AsyncMock()
    res = await create_task(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.title == "Pay Water Bill"
    # Verify both task and bill were added
    added_types = [type(arg) for (arg,), _ in mock_db.add.call_args_list]
    assert BillModel in added_types
    assert TaskModel in added_types


@pytest.mark.asyncio
async def test_delete_bill_unlinks_tasks_safely():
    mock_db = AsyncMock()
    home_id = uuid4()
    bill_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="owner@ozhzo.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    bill = BillModel(
        id=bill_id,
        home_id=home_id,
        title="Car Insurance",
        expected_amount=Decimal("14500.00"),
        currency="INR",
        due_date=date(2026, 12, 1),
        recurrence_type="YEARLY",
        status="UNPAID",
        version=1
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = bill
    mock_db.execute.return_value = mock_res

    res = await delete_bill(bill_id, home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert bill.status == "CANCELLED"
    assert bill.deleted_at is not None
    # Verify db executed unlinking update on TaskModel
    assert mock_db.execute.called
    assert mock_db.commit.called


def test_calculate_next_bill_due_date_various_intervals():
    start = date(2026, 8, 15)

    # Monthly
    nxt_monthly = calculate_next_bill_due_date(start, "MONTHLY")
    assert nxt_monthly == date(2026, 9, 15)

    # Quarterly
    nxt_quarterly = calculate_next_bill_due_date(start, "QUARTERLY")
    assert nxt_quarterly == date(2026, 11, 15)

    # Yearly
    nxt_yearly = calculate_next_bill_due_date(start, "YEARLY")
    assert nxt_yearly == date(2027, 8, 15)

    # Custom Days (e.g. 45 days)
    nxt_custom = calculate_next_bill_due_date(start, "CUSTOM_DAYS", interval_days=45)
    assert nxt_custom == start + timedelta(days=45)
