import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)
from src.schemas.bill import CreateBillRequest, RecordPaymentRequest
from src.api.v1.bills import (
    create_bill,
    record_bill_payment,
    calculate_next_bill_due_date,
    send_bill_due_notification
)
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import BillModel, UserModel, UserProfileModel


def test_recurring_bill_due_calculation():
    # Monthly: Jan 15 -> Feb 15
    due_jan = date(2026, 1, 15)
    due_feb = calculate_next_bill_due_date(due_jan, "MONTHLY")
    assert due_feb == date(2026, 2, 15)

    # Quarterly: Jan 15 -> Apr 15
    due_apr = calculate_next_bill_due_date(due_jan, "QUARTERLY")
    assert due_apr == date(2026, 4, 15)

    # Annual: Jan 15, 2026 -> Jan 15, 2027
    due_next_year = calculate_next_bill_due_date(due_jan, "ANNUAL")
    assert due_next_year == date(2027, 1, 15)


@pytest.mark.asyncio
async def test_create_bill_and_reminders():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)

    req = CreateBillRequest(
        title="Fiber Internet",
        category="Utilities",
        amount=Decimal("79.99"),
        currency="USD",
        due_date=date(2026, 8, 28),
        recurrence_interval="MONTHLY",
        reminder_days_before=[7, 3, 1]
    )

    mock_redis = AsyncMock()
    res = await create_bill(req, home_ctx=ctx, db=mock_db, redis_client=mock_redis)

    assert res.success is True
    assert res.data.title == "Fiber Internet"
    assert res.data.amount == Decimal("79.99")
    assert res.data.status == "UNPAID"
    # Added BillModel + 3 BillReminderModel records = 4 additions
    assert mock_db.add.call_count >= 4


@pytest.mark.asyncio
async def test_record_payment_spawns_recurring_iteration():
    mock_db = AsyncMock()
    home_id = uuid4()
    bill_id = uuid4()
    user_id = uuid4()

    bill = BillModel(
        id=bill_id,
        home_id=home_id,
        title="Power Utility",
        expected_amount=Decimal("120.00"),
        currency="USD",
        due_date=date(2026, 8, 20),
        recurrence_type="MONTHLY",
        status="UNPAID",
        version=1
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = bill
    mock_db.execute.return_value = mock_res

    user = UserModel(id=user_id, email="alex@example.com")
    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    mock_redis = AsyncMock()

    res = await record_bill_payment(
        bill_id,
        payload=RecordPaymentRequest(amount_paid=Decimal("120.00")),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert res.success is True
    assert bill.status == "PAID"
    # Added payment record + next BillModel + next reminder records
    assert mock_db.add.call_count >= 2


@pytest.mark.asyncio
async def test_bill_due_notification():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [user_id]
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res


    await send_bill_due_notification(
        home_id=home_id,
        bill_title="Water Bill",
        amount=Decimal("45.00"),
        currency="USD",
        due_date=date(2026, 8, 25),
        db=mock_db
    )

    assert mock_db.add.call_count >= 1


def test_bills_rbac_privacy_safeguards():
    # Child and Guest have NO access to bills
    assert has_permission(ROLE_CHILD, "bills:view") is False
    assert has_permission(ROLE_CHILD, "bills:pay") is False
    assert has_permission(ROLE_GUEST, "bills:view") is False
    assert has_permission(ROLE_GUEST, "bills:pay") is False

    # Owner, Admin, Member have full bill access
    assert has_permission(ROLE_OWNER, "bills:view") is True
    assert has_permission(ROLE_ADMIN, "bills:create") is True
    assert has_permission(ROLE_MEMBER, "bills:pay") is True
