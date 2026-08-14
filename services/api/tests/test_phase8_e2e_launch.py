import pytest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_phase8_e2e_complete_household_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # =========================================================================
        # SCENARIO 1: New Home Setup & Member Onboarding
        # =========================================================================
        # 1. Register User A (Vivek - Home Owner)
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": "vivek_p8@ozhzo.com",
            "password": "Password123!",
            "full_name": "Vivek Madhavan"
        })
        assert reg_a.status_code == 201
        token_a = reg_a.json()["data"]["tokens"]["access_token"]
        user_a_id = reg_a.json()["data"]["tokens"]["user_id"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Register User B (Karthika - Family Member)
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": "karthika_p8@ozhzo.com",
            "password": "Password123!",
            "full_name": "Karthika Vivek"
        })
        assert reg_b.status_code == 201
        token_b = reg_b.json()["data"]["tokens"]["access_token"]
        user_b_id = reg_b.json()["data"]["tokens"]["user_id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Create Home Workspace (Madhavan Home)
        home_res = await client.post("/api/v1/homes", json={
            "name": "Madhavan Home Pilot",
            "currency": "INR",
            "timezone": "Asia/Kolkata"
        }, headers=headers_a)
        assert home_res.status_code == 201
        home_id = home_res.json()["data"]["id"]

        # 4. Invite & Add Karthika as Active Member
        inv_res = await client.post(f"/api/v1/homes/{home_id}/members", json={
            "email": "karthika_p8@ozhzo.com",
            "role": "MEMBER"
        }, headers=headers_a)
        assert inv_res.status_code == 201

        # =========================================================================
        # SCENARIO 2: Hierarchical Location & Add Rice
        # =========================================================================
        # Create hierarchy: Kitchen -> Pantry -> Shelf 2
        loc_k = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Kitchen",
            "location_type": "ROOM"
        }, headers=headers_a)
        assert loc_k.status_code == 201
        kitchen_id = loc_k.json()["data"]["id"]

        loc_p = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Pantry",
            "location_type": "FURNITURE",
            "parent_id": kitchen_id
        }, headers=headers_a)
        assert loc_p.status_code == 201
        pantry_id = loc_p.json()["data"]["id"]

        loc_s2 = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Shelf 2",
            "location_type": "SHELF",
            "parent_id": pantry_id
        }, headers=headers_a)
        assert loc_s2.status_code == 201
        shelf2_id = loc_s2.json()["data"]["id"]

        # Add Rice: 5 kg, min_threshold 3 kg
        rice_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items", json={
            "name": "Basmati Rice Royal",
            "item_type": "CONSUMABLE",
            "quantity": 5,
            "unit": "kg",
            "min_threshold": 3,
            "location_id": shelf2_id
        }, headers=headers_a)
        assert rice_res.status_code == 201
        rice_id = rice_res.json()["data"]["id"]
        assert "Kitchen" in rice_res.json()["data"]["location_path"]

        # =========================================================================
        # SCENARIO 3: Rice Becomes Low Stock
        # =========================================================================
        # Consume 3 kg -> Quantity becomes 2 kg (<= min_threshold 3)
        mv_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items/{rice_id}/movements", json={
            "movement_type": "CONSUMPTION",
            "quantity": 3,
            "notes": "Cooking family dinner"
        }, headers=headers_a)
        assert mv_res.status_code == 201
        assert Decimal(str(mv_res.json()["data"]["new_quantity"])) == Decimal("2")

        # =========================================================================
        # SCENARIO 4: Add Rice to Purchase List
        # =========================================================================
        pur_res = await client.post(f"/api/v1/homes/{home_id}/purchase-list/items", json={
            "name": "Basmati Rice Royal",
            "quantity": 5,
            "unit": "kg",
            "priority": "HIGH",
            "inventory_item_id": rice_id
        }, headers=headers_b)
        assert pur_res.status_code == 201
        purchase_item_id = pur_res.json()["data"]["id"]

        # =========================================================================
        # SCENARIO 5: Member Buys Rice & Confirms Inventory Restock
        # =========================================================================
        # Check purchase item off and restock inventory
        buy_res = await client.patch(f"/api/v1/homes/{home_id}/purchase-list/items/{purchase_item_id}", json={
            "is_checked": True
        }, headers=headers_b)
        assert buy_res.status_code == 200

        # Restock 5 kg to inventory
        restock_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items/{rice_id}/movements", json={
            "movement_type": "RESTOCK",
            "quantity": 5,
            "notes": "Bought from supermarket"
        }, headers=headers_b)
        assert restock_res.status_code == 201
        assert Decimal(str(restock_res.json()["data"]["new_quantity"])) == Decimal("7")

        # =========================================================================
        # SCENARIO 6: Add Toolkit to Store Room -> 3rd Cupboard -> Blue Box
        # =========================================================================
        loc_sr = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Store Room",
            "location_type": "ROOM"
        }, headers=headers_a)
        assert loc_sr.status_code == 201
        store_room_id = loc_sr.json()["data"]["id"]

        loc_cb = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "3rd Cupboard",
            "location_type": "FURNITURE",
            "parent_id": store_room_id
        }, headers=headers_a)
        assert loc_cb.status_code == 201
        cupboard_id = loc_cb.json()["data"]["id"]

        loc_bb = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Blue Box",
            "location_type": "CONTAINER",
            "parent_id": cupboard_id
        }, headers=headers_a)
        assert loc_bb.status_code == 201
        blue_box_id = loc_bb.json()["data"]["id"]

        toolkit_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items", json={
            "name": "Mechanic Precision Toolkit",
            "item_type": "ASSET",
            "location_id": blue_box_id,
            "condition": "EXCELLENT"
        }, headers=headers_a)
        assert toolkit_res.status_code == 201
        toolkit_id = toolkit_res.json()["data"]["id"]
        assert "Store Room" in toolkit_res.json()["data"]["location_path"]

        # =========================================================================
        # SCENARIO 7: Search "Toolkit" & Retrieve Exact Location
        # =========================================================================
        search_tk = await client.get(f"/api/v1/homes/{home_id}/search?q=toolkit", headers=headers_a)
        assert search_tk.status_code == 200
        tk_results = search_tk.json()["data"]["items"]
        assert len(tk_results) >= 1
        assert tk_results[0]["domain"] == "ASSET"
        assert "Store Room" in tk_results[0]["location_path"]
        assert "Blue Box" in tk_results[0]["location_path"]

        # =========================================================================
        # SCENARIO 8: Borrow Toolkit (Asset Loan)
        # =========================================================================
        today = date.today()
        loan_res = await client.post(f"/api/v1/homes/{home_id}/inventory/assets/{toolkit_id}/borrow", json={
            "borrower_user_id": user_b_id,
            "borrower_name": "Karthika",
            "expected_return_date": (today + timedelta(days=3)).isoformat(),
            "notes": "Fixing bicycle"
        }, headers=headers_a)
        assert loan_res.status_code == 201
        assert loan_res.json()["data"]["status"] == "BORROWED"

        # =========================================================================
        # SCENARIO 9: Return Toolkit to Different Location (Garage)
        # =========================================================================
        loc_g = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Garage Workshop",
            "location_type": "ROOM"
        }, headers=headers_a)
        assert loc_g.status_code == 201
        garage_id = loc_g.json()["data"]["id"]

        return_res = await client.post(f"/api/v1/homes/{home_id}/inventory/assets/{toolkit_id}/return", json={
            "new_location_id": garage_id,
            "condition": "EXCELLENT",
            "notes": "Returned safely to garage"
        }, headers=headers_a)
        assert return_res.status_code == 200
        assert return_res.json()["data"]["status"] == "AVAILABLE"
        assert "Garage Workshop" in return_res.json()["data"]["location_path"]

        # =========================================================================
        # SCENARIO 10: Create Recurring Electricity Bill
        # =========================================================================
        bill_res = await client.post(f"/api/v1/homes/{home_id}/bills", json={
            "title": "BESCOM Electricity Bill",
            "expected_amount": "2500.00",
            "due_date": today.isoformat(),
            "recurrence_type": "MONTHLY",
            "currency": "INR"
        }, headers=headers_a)
        assert bill_res.status_code == 201
        bill_id = bill_res.json()["data"]["id"]
        assert bill_res.json()["data"]["status"] == "UNPAID"

        # =========================================================================
        # SCENARIO 11: Record Partial Payment
        # =========================================================================
        pay_res = await client.post(f"/api/v1/homes/{home_id}/bills/{bill_id}/payments", json={
            "amount_paid": "1000.00",
            "currency": "INR",
            "payment_method": "UPI",
            "reference_number": "UPI-123456",
            "notes": "First installment"
        }, headers=headers_a)
        assert pay_res.status_code == 201
        assert pay_res.json()["data"]["bill_status"] == "PARTIALLY_PAID"
        assert Decimal(str(pay_res.json()["data"]["remaining_balance"])) == Decimal("1500.00")

        # =========================================================================
        # SCENARIO 12: Recurring Household Task & Completion
        # =========================================================================
        task_res = await client.post(f"/api/v1/homes/{home_id}/tasks", json={
            "title": "Clean Water Filter Cartridge",
            "due_date": today.isoformat(),
            "priority": "HIGH",
            "recurrence_type": "WEEKLY",
            "recurrence_interval": 1,
            "recurrence_strategy": "COMPLETION_DATE",
            "assigned_to": user_a_id
        }, headers=headers_a)
        assert task_res.status_code == 201
        task_id = task_res.json()["data"]["id"]

        comp_res = await client.post(f"/api/v1/homes/{home_id}/tasks/{task_id}/complete", json={
            "notes": "Replaced carbon filter"
        }, headers=headers_a)
        assert comp_res.status_code == 200
        assert comp_res.json()["data"]["status"] == "COMPLETED"

        # =========================================================================
        # SCENARIO 13: Family Calendar Event with Participants
        # =========================================================================
        now_utc = datetime.now(timezone.utc)
        evt_res = await client.post(f"/api/v1/homes/{home_id}/events", json={
            "title": "Grandmother's 80th Birthday",
            "start_time": (now_utc + timedelta(hours=2)).isoformat(),
            "end_time": (now_utc + timedelta(hours=5)).isoformat(),
            "location": "Family Heritage Home",
            "is_all_day": False,
            "participant_user_ids": [user_b_id]
        }, headers=headers_a)
        assert evt_res.status_code == 201
        event_id = evt_res.json()["data"]["id"]
        assert len(evt_res.json()["data"]["participants"]) == 1

        # =========================================================================
        # SCENARIO 14: Unified Today & Attention Center Views
        # =========================================================================
        today_view = await client.get(f"/api/v1/homes/{home_id}/today", headers=headers_a)
        assert today_view.status_code == 200
        today_data = today_view.json()["data"]
        assert today_data["summary"]["events_count"] >= 1
        assert today_data["summary"]["bills_count"] >= 1

        attention_view = await client.get(f"/api/v1/homes/{home_id}/attention", headers=headers_a)
        assert attention_view.status_code == 200
        att_data = attention_view.json()["data"]
        assert att_data["summary"]["total_attention_items"] >= 1

        activity_view = await client.get(f"/api/v1/homes/{home_id}/activity", headers=headers_a)
        assert activity_view.status_code == 200
        act_data = activity_view.json()["data"]
        assert len(act_data["items"]) >= 4

        # =========================================================================
        # SCENARIO 15: Cross-Home Security Isolation
        # =========================================================================
        # User C creates an external Home
        reg_c = await client.post("/api/v1/auth/register", json={
            "email": "external_c@ozhzo.com",
            "password": "Password123!",
            "full_name": "External User C"
        })
        token_c = reg_c.json()["data"]["tokens"]["access_token"]
        headers_c = {"Authorization": f"Bearer {token_c}"}

        home_c_res = await client.post("/api/v1/homes", json={"name": "External Home C"}, headers=headers_c)
        home_c_id = home_c_res.json()["data"]["id"]

        # User C queries Home A -> 403 Forbidden
        cross_dash = await client.get(f"/api/v1/homes/{home_id}/dashboard", headers=headers_c)
        assert cross_dash.status_code == 403

        cross_today = await client.get(f"/api/v1/homes/{home_id}/today", headers=headers_c)
        assert cross_today.status_code == 403

        # User C searches for Home A's unique toolkit -> 0 results
        search_c = await client.get(f"/api/v1/homes/{home_c_id}/search?q=Mechanic Precision Toolkit", headers=headers_c)
        assert search_c.status_code == 200
        assert len(search_c.json()["data"]["items"]) == 0
