import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from uuid import UUID, uuid4
from sqlalchemy import select
from src.main import app
from src.core.security import create_access_token, hash_password
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import UserModel, UserProfileModel, BillReminderModel, NotificationModel


async def create_verified_user_and_token(db, email_prefix="bill_tester"):
    user_id = uuid4()
    user = UserModel(
        id=user_id,
        email=f"{email_prefix}_{uuid4().hex[:8]}@ozhzo.com",
        password_hash=hash_password("Password123!"),
        mobile_verified=True,
        is_active=True
    )
    db.add(user)
    prof = UserProfileModel(
        user_id=user_id,
        display_name="Verified Tester",
        timezone="UTC"
    )
    db.add(prof)
    await db.commit()
    token = create_access_token(subject=str(user_id))
    return str(user_id), token


@pytest.mark.asyncio
async def test_water_sewerage_full_payment_consistency_scenario():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            _, token = await create_verified_user_and_token(db, "water_sewerage")
        finally:
            await db.close()

        headers = {"Authorization": f"Bearer {token}"}

        # Create Home
        home_res = await client.post("/api/v1/homes", json={
            "name": "Consistency Household",
            "currency": "INR"
        }, headers=headers)
        assert home_res.status_code == 201
        home_id = home_res.json()["data"]["id"]

        # 1. Create one-off bill: Water / sewage cleaning, Amount 650, Due in 5 days, Reminder days before
        future_due = (date.today() + timedelta(days=5)).isoformat()
        create_res = await client.post(f"/api/v1/homes/{home_id}/bills", json={
            "title": "Water / sewage cleaning",
            "expected_amount": "650.00",
            "currency": "INR",
            "due_date": future_due,
            "recurrence_type": "NONE",
            "reminder_days_before": [3, 1]
        }, headers=headers)
        assert create_res.status_code == 201
        bill = create_res.json()["data"]
        bill_id = bill["id"]
        assert bill["title"] == "Water / sewage cleaning"
        assert float(bill["expected_amount"]) == 650.0
        assert float(bill["remaining_balance"]) == 650.0
        assert bill["status"] == "UNPAID"

        # 2. Verify bill is in Upcoming view before payment
        upcoming_res = await client.get(f"/api/v1/homes/{home_id}/bills?view=upcoming", headers=headers)
        assert upcoming_res.status_code == 200
        upcoming_items = upcoming_res.json()["data"]["items"]
        assert len(upcoming_items) == 1
        assert upcoming_items[0]["id"] == bill_id

        # Verify Dashboard upcoming_bills contains it
        dash_res = await client.get(f"/api/v1/homes/{home_id}/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()["data"]
        assert len(dash_data["upcoming_bills"]) == 1
        assert dash_data["upcoming_bills"][0]["id"] == bill_id
        assert dash_data["summary"]["unpaid_bills_count"] == 1
        assert float(dash_data["summary"]["unpaid_bills_sum"]) == 650.0

        # Verify Today view upcoming contains it
        today_res = await client.get(f"/api/v1/homes/{home_id}/today", headers=headers)
        assert today_res.status_code == 200
        today_bills = today_res.json()["data"]["bills"]["upcoming"]
        assert len(today_bills) == 1
        assert today_bills[0]["id"] == bill_id

        # 3. Record payment of 650.00
        pay_res = await client.post(f"/api/v1/homes/{home_id}/bills/{bill_id}/payments", json={
            "amount_paid": "650.00",
            "payment_method": "UPI",
            "paid_date": date.today().isoformat(),
            "notes": "Full settlement via GPay"
        }, headers=headers)
        assert pay_res.status_code == 201
        paid_bill = pay_res.json()["data"]
        assert paid_bill["status"] == "PAID"
        assert float(paid_bill["amount_paid"]) == 650.0
        assert float(paid_bill["remaining_balance"]) == 0.0

        # Verify reminders are marked as sent/resolved
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            b_uuid = UUID(bill_id)
            reminders = (await db.execute(
                select(BillReminderModel).where(BillReminderModel.bill_id == b_uuid)
            )).scalars().all()
            for r in reminders:
                assert r.is_sent is True
        finally:
            await db.close()

        # 4. Verify bill is completely EXCLUDED from Upcoming view
        upcoming_after = await client.get(f"/api/v1/homes/{home_id}/bills?view=upcoming", headers=headers)
        assert upcoming_after.status_code == 200
        assert len(upcoming_after.json()["data"]["items"]) == 0

        # Verify bill is EXCLUDED from Due Today and Overdue views
        due_today_after = await client.get(f"/api/v1/homes/{home_id}/bills?view=due_today", headers=headers)
        assert due_today_after.status_code == 200
        assert len(due_today_after.json()["data"]["items"]) == 0

        overdue_after = await client.get(f"/api/v1/homes/{home_id}/bills?view=overdue", headers=headers)
        assert overdue_after.status_code == 200
        assert len(overdue_after.json()["data"]["items"]) == 0

        # Verify bill is PRESENT in Paid view
        paid_view = await client.get(f"/api/v1/homes/{home_id}/bills?view=paid", headers=headers)
        assert paid_view.status_code == 200
        paid_items = paid_view.json()["data"]["items"]
        assert len(paid_items) == 1
        assert paid_items[0]["id"] == bill_id
        assert paid_items[0]["status"] == "PAID"
        assert float(paid_items[0]["remaining_balance"]) == 0.0

        # 5. Verify Bills Summary KPI
        summary_res = await client.get(f"/api/v1/homes/{home_id}/bills/summary", headers=headers)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()["data"]
        assert summary_data["total_unpaid_count"] == 0
        assert float(summary_data["total_unpaid_amount"]) == 0.0
        assert summary_data["upcoming_count"] == 0
        assert float(summary_data["upcoming_amount"]) == 0.0
        assert summary_data["paid_this_month_count"] == 1
        assert float(summary_data["paid_this_month_amount"]) == 650.0

        # 6. Verify Dashboard excludes it from upcoming_bills and shows 0 unpaid
        dash_after = await client.get(f"/api/v1/homes/{home_id}/dashboard", headers=headers)
        assert dash_after.status_code == 200
        dash_after_data = dash_after.json()["data"]
        assert len(dash_after_data["upcoming_bills"]) == 0
        assert dash_after_data["summary"]["unpaid_bills_count"] == 0
        assert float(dash_after_data["summary"]["unpaid_bills_sum"]) == 0.0

        # 7. Verify Today view has 0 upcoming bills
        today_after = await client.get(f"/api/v1/homes/{home_id}/today", headers=headers)
        assert today_after.status_code == 200
        assert len(today_after.json()["data"]["bills"]["upcoming"]) == 0
        assert len(today_after.json()["data"]["bills"]["due_today"]) == 0
        assert len(today_after.json()["data"]["bills"]["overdue"]) == 0


@pytest.mark.asyncio
async def test_partial_payment_and_multi_installment_consistency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            _, token = await create_verified_user_and_token(db, "partial_tester")
        finally:
            await db.close()

        headers = {"Authorization": f"Bearer {token}"}
        home_res = await client.post("/api/v1/homes", json={"name": "Partial Home", "currency": "INR"}, headers=headers)
        assert home_res.status_code == 201
        home_id = home_res.json()["data"]["id"]

        future_due = (date.today() + timedelta(days=7)).isoformat()
        create_res = await client.post(f"/api/v1/homes/{home_id}/bills", json={
            "title": "Quarterly Maintenance",
            "expected_amount": "650.00",
            "currency": "INR",
            "due_date": future_due,
            "recurrence_type": "NONE"
        }, headers=headers)
        assert create_res.status_code == 201
        bill_id = create_res.json()["data"]["id"]

        # Installment 1: Pay 300.00
        pay1 = await client.post(f"/api/v1/homes/{home_id}/bills/{bill_id}/payments", json={
            "amount_paid": "300.00",
            "payment_method": "UPI"
        }, headers=headers)
        assert pay1.status_code == 201
        data1 = pay1.json()["data"]
        assert data1["status"] == "PARTIALLY_PAID"
        assert float(data1["amount_paid"]) == 300.0
        assert float(data1["remaining_balance"]) == 350.0

        upcoming = await client.get(f"/api/v1/homes/{home_id}/bills?view=upcoming", headers=headers)
        items = upcoming.json()["data"]["items"]
        assert len(items) == 1
        assert float(items[0]["remaining_balance"]) == 350.0
        assert items[0]["status"] == "PARTIALLY_PAID"

        dash = await client.get(f"/api/v1/homes/{home_id}/dashboard", headers=headers)
        assert len(dash.json()["data"]["upcoming_bills"]) == 1
        assert float(dash.json()["data"]["upcoming_bills"][0]["amount"]) == 350.0
        assert float(dash.json()["data"]["summary"]["unpaid_bills_sum"]) == 350.0

        # Installment 2: Pay remaining 350.00
        pay2 = await client.post(f"/api/v1/homes/{home_id}/bills/{bill_id}/payments", json={
            "amount_paid": "350.00",
            "payment_method": "UPI"
        }, headers=headers)
        assert pay2.status_code == 201
        data2 = pay2.json()["data"]
        assert data2["status"] == "PAID"
        assert float(data2["amount_paid"]) == 650.0
        assert float(data2["remaining_balance"]) == 0.0

        upcoming_after = await client.get(f"/api/v1/homes/{home_id}/bills?view=upcoming", headers=headers)
        assert len(upcoming_after.json()["data"]["items"]) == 0

        paid_view = await client.get(f"/api/v1/homes/{home_id}/bills?view=paid", headers=headers)
        assert len(paid_view.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_overpayment_consistency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            _, token = await create_verified_user_and_token(db, "overpay_tester")
        finally:
            await db.close()

        headers = {"Authorization": f"Bearer {token}"}
        home_res = await client.post("/api/v1/homes", json={"name": "Overpay Home", "currency": "INR"}, headers=headers)
        assert home_res.status_code == 201
        home_id = home_res.json()["data"]["id"]

        future_due = (date.today() + timedelta(days=4)).isoformat()
        create_res = await client.post(f"/api/v1/homes/{home_id}/bills", json={
            "title": "Water / sewage cleaning",
            "expected_amount": "650.00",
            "currency": "INR",
            "due_date": future_due,
            "recurrence_type": "NONE"
        }, headers=headers)
        assert create_res.status_code == 201
        bill_id = create_res.json()["data"]["id"]

        # Pay 700.00 (Overpayment)
        pay_res = await client.post(f"/api/v1/homes/{home_id}/bills/{bill_id}/payments", json={
            "amount_paid": "700.00",
            "payment_method": "CASH"
        }, headers=headers)
        assert pay_res.status_code == 201
        data = pay_res.json()["data"]
        assert data["status"] == "PAID"
        assert float(data["remaining_balance"]) == 0.0

        # Excluded from upcoming
        upcoming_after = await client.get(f"/api/v1/homes/{home_id}/bills?view=upcoming", headers=headers)
        assert len(upcoming_after.json()["data"]["items"]) == 0


@pytest.mark.asyncio
async def test_recurring_bill_cycle_generation_and_separation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            _, token = await create_verified_user_and_token(db, "recur_tester")
        finally:
            await db.close()

        headers = {"Authorization": f"Bearer {token}"}
        home_res = await client.post("/api/v1/homes", json={"name": "Recurring Home", "currency": "INR"}, headers=headers)
        assert home_res.status_code == 201
        home_id = home_res.json()["data"]["id"]

        today_d = date.today()
        create_res = await client.post(f"/api/v1/homes/{home_id}/bills", json={
            "title": "Fiber Broadband",
            "expected_amount": "999.00",
            "currency": "INR",
            "due_date": today_d.isoformat(),
            "recurrence_type": "MONTHLY"
        }, headers=headers)
        assert create_res.status_code == 201
        orig_bill = create_res.json()["data"]
        orig_id = orig_bill["id"]

        pay_res = await client.post(f"/api/v1/homes/{home_id}/bills/{orig_id}/payments", json={
            "amount_paid": "999.00",
            "payment_method": "UPI"
        }, headers=headers)
        assert pay_res.status_code == 201
        assert pay_res.json()["data"]["status"] == "PAID"

        # Upcoming view should have only the newly scheduled next-cycle bill
        upcoming_res = await client.get(f"/api/v1/homes/{home_id}/bills?view=upcoming", headers=headers)
        items = upcoming_res.json()["data"]["items"]

        assert len(items) == 1
        new_cycle_bill = items[0]
        assert new_cycle_bill["id"] != orig_id
        assert new_cycle_bill["status"] == "UNPAID"
        assert float(new_cycle_bill["amount_paid"]) == 0.0
        assert float(new_cycle_bill["remaining_balance"]) == 999.0
        assert new_cycle_bill["parent_recurring_bill_id"] == orig_id
        assert new_cycle_bill["due_date"] > today_d.isoformat()

        # Paid view has the original bill
        paid_res = await client.get(f"/api/v1/homes/{home_id}/bills?view=paid", headers=headers)
        paid_items = paid_res.json()["data"]["items"]
        assert len(paid_items) == 1
        assert paid_items[0]["id"] == orig_id
        assert paid_items[0]["status"] == "PAID"
