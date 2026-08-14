import pytest
from datetime import date, datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_phase5_bills_complete_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Users & Homes
        # User A1 (Home Owner / Admin)
        u_a1 = await client.post("/api/v1/auth/register", json={
            "email": "vivek_bills@ozhzo.com",
            "password": "Password123!",
            "full_name": "Vivek Madhavan"
        })
        token_a1 = u_a1.json()["data"]["tokens"]["access_token"]
        user_a1_id = u_a1.json()["data"]["tokens"]["user_id"]
        headers_a1 = {"Authorization": f"Bearer {token_a1}"}

        # User A2 (Home Member)
        u_a2 = await client.post("/api/v1/auth/register", json={
            "email": "karthika_bills@ozhzo.com",
            "password": "Password123!",
            "full_name": "Karthika Vivek"
        })
        token_a2 = u_a2.json()["data"]["tokens"]["access_token"]
        user_a2_id = u_a2.json()["data"]["tokens"]["user_id"]
        headers_a2 = {"Authorization": f"Bearer {token_a2}"}

        # User B (Different Home Owner)
        u_b = await client.post("/api/v1/auth/register", json={
            "email": "external_user_bills@ozhzo.com",
            "password": "Password123!",
            "full_name": "External User"
        })
        token_b = u_b.json()["data"]["tokens"]["access_token"]
        user_b_id = u_b.json()["data"]["tokens"]["user_id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Home A & Home B
        home_a_res = await client.post("/api/v1/homes", json={"name": "Madhavan Home Bills", "currency": "INR"}, headers=headers_a1)
        home_a_id = home_a_res.json()["data"]["id"]

        home_b_res = await client.post("/api/v1/homes", json={"name": "External Home Bills", "currency": "USD"}, headers=headers_b)
        home_b_id = home_b_res.json()["data"]["id"]

        # Add User A2 as active member of Home A
        inv_res = await client.post(f"/api/v1/homes/{home_a_id}/members", json={
            "email": "karthika_bills@ozhzo.com",
            "role": "MEMBER"
        }, headers=headers_a1)
        assert inv_res.status_code == 201

        # -------------------------------------------------------------
        # 1. Global Bill Templates Catalog
        # -------------------------------------------------------------
        tpl_res = await client.get("/api/v1/bill-templates", headers=headers_a1)
        assert tpl_res.status_code == 200
        tpl_items = tpl_res.json()["data"]
        assert len(tpl_items) >= 5
        assert any(t["name"] == "Electricity Bill" for t in tpl_items)

        # -------------------------------------------------------------
        # 2. Bill Categories Management
        # -------------------------------------------------------------
        cat_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/categories", json={
            "name": "Utilities",
            "icon": "zap",
            "color": "#f59e0b"
        }, headers=headers_a1)
        assert cat_res.status_code == 201
        cat_id = cat_res.json()["data"]["id"]

        # Duplicate category in same home rejected
        dup_cat_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/categories", json={
            "name": "Utilities"
        }, headers=headers_a1)
        assert dup_cat_res.status_code == 400

        # -------------------------------------------------------------
        # 3. Quick Bill Creation (Title, Expected Amount, Due Date)
        # -------------------------------------------------------------
        today_str = date.today().isoformat()
        q_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Internet Subscription",
            "expected_amount": "999.00",
            "due_date": today_str
        }, headers=headers_a1)
        assert q_res.status_code == 201
        q_bill = q_res.json()["data"]
        assert q_bill["title"] == "Internet Subscription"
        assert float(q_bill["expected_amount"]) == 999.0
        assert q_bill["status"] == "UNPAID"
        assert q_bill["is_due_today"] is True
        assert q_bill["is_overdue"] is False
        assert float(q_bill["remaining_balance"]) == 999.0
        assert q_bill["currency"] == "INR"

        # -------------------------------------------------------------
        # 4. Responsible Member Validation (Cross-Home Rejection)
        # -------------------------------------------------------------
        # Assign to User B (Not in Home A) -> 400
        invalid_resp_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Water Bill",
            "expected_amount": "500.00",
            "due_date": today_str,
            "responsible_member_id": user_b_id
        }, headers=headers_a1)
        assert invalid_resp_res.status_code == 400

        # Assign to User A2 (Active in Home A) -> 201
        valid_resp_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "BESCOM Electricity Bill",
            "expected_amount": "2000.00",
            "due_date": today_str,
            "category_id": cat_id,
            "recurrence_type": "MONTHLY",
            "recurrence_strategy": "SCHEDULED_DATE",
            "responsible_member_id": user_a2_id
        }, headers=headers_a1)
        assert valid_resp_res.status_code == 201
        elec_bill = valid_resp_res.json()["data"]
        elec_bill_id = elec_bill["id"]
        assert elec_bill["responsible_member_name"] == "Karthika Vivek"

        # -------------------------------------------------------------
        # 5. Financial Hardening: Negative & Zero Payment Rejection
        # -------------------------------------------------------------
        neg_pay = await client.post(f"/api/v1/homes/{home_a_id}/bills/{elec_bill_id}/payments", json={
            "amount_paid": "-500.00"
        }, headers=headers_a1)
        assert neg_pay.status_code == 422

        zero_pay = await client.post(f"/api/v1/homes/{home_a_id}/bills/{elec_bill_id}/payments", json={
            "amount_paid": "0.00"
        }, headers=headers_a1)
        assert zero_pay.status_code == 422

        # -------------------------------------------------------------
        # 6. Financial Hardening: Currency Mismatch Rejection
        # -------------------------------------------------------------
        curr_mismatch = await client.post(f"/api/v1/homes/{home_a_id}/bills/{elec_bill_id}/payments", json={
            "amount_paid": "100.00",
            "currency": "USD"
        }, headers=headers_a1)
        assert curr_mismatch.status_code == 400
        assert "Currency mismatch" in curr_mismatch.json()["detail"]

        # -------------------------------------------------------------
        # 7. Variable Utility Payment Recording (Expected vs Actual)
        # -------------------------------------------------------------
        # Expected is 2000, Actual Paid is 2137
        pay_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/{elec_bill_id}/payments", json={
            "amount_paid": "2137.00",
            "currency": "INR",
            "payment_method": "UPI",
            "notes": "Paid via GooglePay Txn #99410"
        }, headers=headers_a1)
        assert pay_res.status_code == 201
        paid_bill = pay_res.json()["data"]
        assert paid_bill["status"] == "PAID"
        assert float(paid_bill["expected_amount"]) == 2000.0  # Expected baseline preserved!
        assert float(paid_bill["amount_paid"]) == 2137.0      # Actual paid aggregated!
        assert float(paid_bill["remaining_balance"]) == 0.0

        # Check that recurring next occurrence was spawned automatically
        bills_list_res = await client.get(f"/api/v1/homes/{home_a_id}/bills?view=all", headers=headers_a1)
        active_items = [b for b in bills_list_res.json()["data"]["items"] if b["title"] == "BESCOM Electricity Bill" and b["status"] == "UNPAID"]
        assert len(active_items) == 1
        next_elec = active_items[0]
        assert next_elec["parent_recurring_bill_id"] == elec_bill_id
        assert next_elec["status"] == "UNPAID"
        assert float(next_elec["amount_paid"]) == 0.0
        assert float(next_elec["expected_amount"]) == 2000.0

        # -------------------------------------------------------------
        # 8. Financial Hardening: Additional Payment on PAID Bill Rejection
        # -------------------------------------------------------------
        extra_pay = await client.post(f"/api/v1/homes/{home_a_id}/bills/{elec_bill_id}/payments", json={
            "amount_paid": "100.00"
        }, headers=headers_a1)
        assert extra_pay.status_code == 400
        assert "already been fully paid" in extra_pay.json()["detail"]

        # -------------------------------------------------------------
        # 9. Partial Payments & Remaining Balance
        # -------------------------------------------------------------
        school_due = (date.today() + timedelta(days=10)).isoformat()
        school_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "School Tuition Fee",
            "expected_amount": "10000.00",
            "due_date": school_due
        }, headers=headers_a1)
        assert school_res.status_code == 201
        school_bill_id = school_res.json()["data"]["id"]

        # First partial payment of ₹6,000
        p1_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/{school_bill_id}/payments", json={
            "amount_paid": "6000.00",
            "payment_method": "BANK_TRANSFER",
            "notes": "First installment"
        }, headers=headers_a1)
        assert p1_res.status_code == 201
        p1_bill = p1_res.json()["data"]
        assert p1_bill["status"] == "PARTIALLY_PAID"
        assert float(p1_bill["amount_paid"]) == 6000.0
        assert float(p1_bill["remaining_balance"]) == 4000.0

        # Second partial payment of ₹4,000 -> Transitions to PAID
        p2_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/{school_bill_id}/payments", json={
            "amount_paid": "4000.00",
            "payment_method": "UPI",
            "notes": "Second installment (final)"
        }, headers=headers_a2)
        assert p2_res.status_code == 201
        p2_bill = p2_res.json()["data"]
        assert p2_bill["status"] == "PAID"
        assert float(p2_bill["amount_paid"]) == 10000.0
        assert float(p2_bill["remaining_balance"]) == 0.0

        # -------------------------------------------------------------
        # 10. Financial Hardening: Exact Overpayment Handling
        # -------------------------------------------------------------
        overpay_due = (date.today() + timedelta(days=5)).isoformat()
        overpay_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Water Tank Cleaning",
            "expected_amount": "1000.00",
            "due_date": overpay_due
        }, headers=headers_a1)
        assert overpay_res.status_code == 201
        overpay_bill_id = overpay_res.json()["data"]["id"]

        # Pay ₹1,200 on ₹1,000 expected bill
        op_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/{overpay_bill_id}/payments", json={
            "amount_paid": "1200.00",
            "notes": "Includes tip for cleaning crew"
        }, headers=headers_a1)
        assert op_res.status_code == 201
        op_bill = op_res.json()["data"]
        assert op_bill["status"] == "PAID"
        assert float(op_bill["expected_amount"]) == 1000.0
        assert float(op_bill["amount_paid"]) == 1200.0
        assert float(op_bill["remaining_balance"]) == 0.0

        # -------------------------------------------------------------
        # 11. Immutable Payment Ledger History
        # -------------------------------------------------------------
        history_res = await client.get(f"/api/v1/homes/{home_a_id}/bills/{school_bill_id}/payments", headers=headers_a1)
        assert history_res.status_code == 200
        ledger = history_res.json()["data"]
        assert len(ledger) == 2
        assert float(ledger[0]["amount_paid"]) == 4000.0
        assert float(ledger[1]["amount_paid"]) == 6000.0
        assert ledger[0]["paid_by_name"] == "Karthika Vivek"

        # -------------------------------------------------------------
        # 12. Overdue & Time Derivations
        # -------------------------------------------------------------
        overdue_due = (date.today() - timedelta(days=3)).isoformat()
        od_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Property Tax Assessment",
            "expected_amount": "5000.00",
            "due_date": overdue_due
        }, headers=headers_a1)
        assert od_res.status_code == 201
        od_bill = od_res.json()["data"]
        assert od_bill["is_overdue"] is True
        assert od_bill["is_due_today"] is False

        # -------------------------------------------------------------
        # 13. View Filters & Summary Metrics
        # -------------------------------------------------------------
        today_view = await client.get(f"/api/v1/homes/{home_a_id}/bills?view=due_today", headers=headers_a1)
        assert today_view.status_code == 200
        assert all(b["is_due_today"] for b in today_view.json()["data"]["items"])

        overdue_view = await client.get(f"/api/v1/homes/{home_a_id}/bills?view=overdue", headers=headers_a1)
        assert overdue_view.status_code == 200
        assert all(b["is_overdue"] for b in overdue_view.json()["data"]["items"])

        summary_res = await client.get(f"/api/v1/homes/{home_a_id}/bills/summary", headers=headers_a1)
        assert summary_res.status_code == 200
        summary = summary_res.json()["data"]
        assert summary["due_today_count"] >= 1
        assert summary["overdue_count"] >= 1
        assert float(summary["paid_this_month_amount"]) >= 13337.0  # 2137 + 6000 + 4000 + 1200

        # -------------------------------------------------------------
        # 14. Financial Hardening: Decimal Precision Testing
        # -------------------------------------------------------------
        prec_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Micro Precision Test",
            "expected_amount": "0.01",
            "due_date": today_str
        }, headers=headers_a1)
        assert prec_res.status_code == 201
        prec_id = prec_res.json()["data"]["id"]

        p_prec = await client.post(f"/api/v1/homes/{home_a_id}/bills/{prec_id}/payments", json={
            "amount_paid": "0.01"
        }, headers=headers_a1)
        assert p_prec.status_code == 201
        assert p_prec.json()["data"]["status"] == "PAID"
        assert float(p_prec.json()["data"]["amount_paid"]) == 0.01

        # -------------------------------------------------------------
        # 15. Optimistic Locking (Version Conflict 409)
        # -------------------------------------------------------------
        detail_res = await client.get(f"/api/v1/homes/{home_a_id}/bills/{od_bill['id']}", headers=headers_a1)
        v = detail_res.json()["data"]["version"]

        conflict_res = await client.patch(f"/api/v1/homes/{home_a_id}/bills/{od_bill['id']}", json={
            "title": "Updated Title",
            "version": v + 999
        }, headers=headers_a1)
        assert conflict_res.status_code == 409

        # -------------------------------------------------------------
        # 16. Soft-Delete / Cancel & Cancelled Bill Behavior
        # -------------------------------------------------------------
        del_res = await client.delete(f"/api/v1/homes/{home_a_id}/bills/{od_bill['id']}", headers=headers_a1)
        assert del_res.status_code == 200

        # Payment against cancelled bill rejected
        pay_cancelled = await client.post(f"/api/v1/homes/{home_a_id}/bills/{od_bill['id']}/payments", json={
            "amount_paid": "5000.00"
        }, headers=headers_a1)
        assert pay_cancelled.status_code == 404 or pay_cancelled.status_code == 400

        # -------------------------------------------------------------
        # 17. Multi-Home Security Isolation (Cross-Home 403)
        # -------------------------------------------------------------
        # User B cannot access Home A bills
        cross_home_res = await client.get(f"/api/v1/homes/{home_a_id}/bills", headers=headers_b)
        assert cross_home_res.status_code == 403

        # User B cannot record payment for Home A bill
        cross_pay_res = await client.post(f"/api/v1/homes/{home_a_id}/bills/{school_bill_id}/payments", json={
            "amount_paid": "100.00"
        }, headers=headers_b)
        assert cross_pay_res.status_code == 403
