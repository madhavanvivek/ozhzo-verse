import pytest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_pilot_smoke_test_complete_journey():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # =========================================================================
        # 1. Register & Verify Mobile (Owner)
        # =========================================================================
        reg_owner = await client.post("/api/v1/auth/register", json={
            "email": "pilot_owner@ozhzo.com",
            "password": "PilotPassword123!",
            "full_name": "Alex Pilot"
        })
        assert reg_owner.status_code == 201
        owner_token = reg_owner.json()["data"]["tokens"]["access_token"]
        owner_id = reg_owner.json()["data"]["tokens"]["user_id"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # Verify profile
        profile_res = await client.get("/api/v1/users/profile", headers=owner_headers)
        assert profile_res.status_code == 200
        assert profile_res.json()["data"]["display_name"] == "Alex Pilot"

        # =========================================================================
        # 2. Create Home & Become HOME_ADMIN / OWNER
        # =========================================================================
        home_res = await client.post("/api/v1/homes", json={
            "name": "Rivera Pilot Household",
            "currency": "USD",
            "timezone": "America/New_York"
        }, headers=owner_headers)
        assert home_res.status_code == 201
        home_id = home_res.json()["data"]["id"]

        # =========================================================================
        # 3. Invite Member & Member Accepts / Joins
        # =========================================================================
        reg_member = await client.post("/api/v1/auth/register", json={
            "email": "pilot_member@ozhzo.com",
            "password": "PilotPassword123!",
            "full_name": "Sarah Pilot"
        })
        assert reg_member.status_code == 201
        member_token = reg_member.json()["data"]["tokens"]["access_token"]
        member_id = reg_member.json()["data"]["tokens"]["user_id"]
        member_headers = {"Authorization": f"Bearer {member_token}"}

        # Owner adds Sarah as MEMBER
        inv_res = await client.post(f"/api/v1/homes/{home_id}/members", json={
            "email": "pilot_member@ozhzo.com",
            "role": "MEMBER"
        }, headers=owner_headers)
        assert inv_res.status_code == 201

        # Verify member list in Home
        members_list = await client.get(f"/api/v1/homes/{home_id}/members", headers=owner_headers)
        assert members_list.status_code == 200
        assert len(members_list.json()["data"]) == 2

        # =========================================================================
        # 4. Home Dashboard Pulse
        # =========================================================================
        dash_res = await client.get(f"/api/v1/homes/{home_id}/dashboard", headers=owner_headers)
        assert dash_res.status_code == 200
        assert dash_res.json()["data"]["summary"]["home_name"] == "Rivera Pilot Household"

        # =========================================================================
        # 5. Add Location & Hierarchical Structure
        # =========================================================================
        loc_room = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Store Room",
            "location_type": "ROOM"
        }, headers=owner_headers)
        assert loc_room.status_code == 201
        store_room_id = loc_room.json()["data"]["id"]

        loc_cupboard = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "3rd Cupboard",
            "location_type": "FURNITURE",
            "parent_id": store_room_id
        }, headers=owner_headers)
        assert loc_cupboard.status_code == 201
        cupboard_id = loc_cupboard.json()["data"]["id"]

        loc_box = await client.post(f"/api/v1/homes/{home_id}/locations", json={
            "name": "Blue Box",
            "location_type": "CONTAINER",
            "parent_id": cupboard_id
        }, headers=owner_headers)
        assert loc_box.status_code == 201
        blue_box_id = loc_box.json()["data"]["id"]

        # =========================================================================
        # 6. Add Consumable Inventory Item & Durable Asset
        # =========================================================================
        # Add Rice (Consumable)
        rice_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items", json={
            "name": "Basmati Rice Royal",
            "item_type": "CONSUMABLE",
            "quantity": 5,
            "unit": "kg",
            "min_threshold": 3,
            "location_id": store_room_id
        }, headers=owner_headers)
        assert rice_res.status_code == 201
        rice_id = rice_res.json()["data"]["id"]

        # Add Toolkit (Durable Asset)
        toolkit_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items", json={
            "name": "Mechanic Precision Toolkit",
            "item_type": "ASSET",
            "location_id": blue_box_id,
            "condition": "EXCELLENT"
        }, headers=owner_headers)
        assert toolkit_res.status_code == 201
        toolkit_id = toolkit_res.json()["data"]["id"]

        # =========================================================================
        # 7. Search Home Memory (Deterministic Search)
        # =========================================================================
        search_res = await client.get(f"/api/v1/homes/{home_id}/search?q=toolkit", headers=owner_headers)
        assert search_res.status_code == 200
        items = search_res.json()["data"]["items"]
        assert len(items) >= 1
        assert items[0]["domain"] == "ASSET"
        assert "Store Room" in items[0]["location_path"]
        assert "Blue Box" in items[0]["location_path"]

        # =========================================================================
        # 8. Add Purchase List Item -> Complete Purchase -> Update Inventory
        # =========================================================================
        pur_res = await client.post(f"/api/v1/homes/{home_id}/purchase-list/items", json={
            "name": "Basmati Rice Royal",
            "quantity": 5,
            "unit": "kg",
            "priority": "HIGH",
            "inventory_item_id": rice_id
        }, headers=member_headers)
        assert pur_res.status_code == 201
        pur_item_id = pur_res.json()["data"]["id"]

        # Complete purchase
        check_pur = await client.patch(f"/api/v1/homes/{home_id}/purchase-list/items/{pur_item_id}", json={
            "is_checked": True
        }, headers=member_headers)
        assert check_pur.status_code == 200

        # Restock inventory
        restock_res = await client.post(f"/api/v1/homes/{home_id}/inventory/items/{rice_id}/movements", json={
            "movement_type": "RESTOCK",
            "quantity": 5,
            "notes": "Restocked from supermarket"
        }, headers=member_headers)
        assert restock_res.status_code == 201
        assert Decimal(str(restock_res.json()["data"]["new_quantity"])) == Decimal("10")

        # =========================================================================
        # 9. Create Task -> Complete Task
        # =========================================================================
        today = date.today()
        task_res = await client.post(f"/api/v1/homes/{home_id}/tasks", json={
            "title": "Clean Water Filter Cartridge",
            "due_date": today.isoformat(),
            "priority": "HIGH",
            "assigned_to": member_id
        }, headers=owner_headers)
        assert task_res.status_code == 201
        task_id = task_res.json()["data"]["id"]

        complete_task = await client.post(f"/api/v1/homes/{home_id}/tasks/{task_id}/complete", json={
            "notes": "Replaced filter element"
        }, headers=member_headers)
        assert complete_task.status_code == 200
        assert complete_task.json()["data"]["status"] == "COMPLETED"

        # =========================================================================
        # 10. Create Bill -> Record Payment
        # =========================================================================
        bill_res = await client.post(f"/api/v1/homes/{home_id}/bills", json={
            "title": "City Electricity Utility",
            "expected_amount": "150.00",
            "due_date": today.isoformat(),
            "currency": "USD"
        }, headers=owner_headers)
        assert bill_res.status_code == 201
        bill_id = bill_res.json()["data"]["id"]

        pay_res = await client.post(f"/api/v1/homes/{home_id}/bills/{bill_id}/payments", json={
            "amount_paid": "150.00",
            "currency": "USD",
            "payment_method": "ONLINE_TRANSFER",
            "reference_number": "TXN-987654"
        }, headers=owner_headers)
        assert pay_res.status_code == 201
        assert pay_res.json()["data"]["bill_status"] == "PAID"
        assert Decimal(str(pay_res.json()["data"]["remaining_balance"])) == Decimal("0.00")

        # =========================================================================
        # 11. Create Calendar Event & RSVP
        # =========================================================================
        now_utc = datetime.now(timezone.utc)
        evt_res = await client.post(f"/api/v1/homes/{home_id}/events", json={
            "title": "Grandmother's 80th Birthday Celebration",
            "start_time": (now_utc + timedelta(hours=2)).isoformat(),
            "end_time": (now_utc + timedelta(hours=5)).isoformat(),
            "location": "Family Dining Room",
            "participant_user_ids": [member_id]
        }, headers=owner_headers)
        assert evt_res.status_code == 201
        event_id = evt_res.json()["data"]["id"]

        rsvp_res = await client.post(f"/api/v1/homes/{home_id}/events/{event_id}/participants/{member_id}/status", json={
            "status": "ACCEPTED"
        }, headers=member_headers)
        assert rsvp_res.status_code == 200

        # =========================================================================
        # 12. View Today View & Attention Center
        # =========================================================================
        today_view = await client.get(f"/api/v1/homes/{home_id}/today", headers=owner_headers)
        assert today_view.status_code == 200
        assert today_view.json()["data"]["summary"]["events_count"] >= 1

        attention_view = await client.get(f"/api/v1/homes/{home_id}/attention", headers=owner_headers)
        assert attention_view.status_code == 200

        # =========================================================================
        # 13. Critical Security Verification (Cross-Home & Forgery)
        # =========================================================================
        # User X creates Home X
        reg_x = await client.post("/api/v1/auth/register", json={
            "email": "attacker_x@ozhzo.com",
            "password": "AttackerPass123!",
            "full_name": "Attacker X"
        })
        token_x = reg_x.json()["data"]["tokens"]["access_token"]
        headers_x = {"Authorization": f"Bearer {token_x}"}

        home_x = await client.post("/api/v1/homes", json={"name": "Attacker Home"}, headers=headers_x)
        home_x_id = home_x.json()["data"]["id"]

        # 13a. Cross-Home Dashboard Access -> 403 Forbidden
        cross_dash = await client.get(f"/api/v1/homes/{home_id}/dashboard", headers=headers_x)
        assert cross_dash.status_code == 403

        # 13b. Cross-Home Today Access -> 403 Forbidden
        cross_today = await client.get(f"/api/v1/homes/{home_id}/today", headers=headers_x)
        assert cross_today.status_code == 403

        # 13c. Cross-Home Search Leakage -> 0 results
        cross_search = await client.get(f"/api/v1/homes/{home_x_id}/search?q=Mechanic Precision Toolkit", headers=headers_x)
        assert cross_search.status_code == 200
        assert len(cross_search.json()["data"]["items"]) == 0

        # 13d. Cross-Home Asset Borrowing IDOR -> 403 Forbidden
        cross_borrow = await client.post(f"/api/v1/homes/{home_id}/inventory/assets/{toolkit_id}/borrow", json={
            "borrower_name": "Attacker",
            "expected_return_date": (today + timedelta(days=2)).isoformat()
        }, headers=headers_x)
        assert cross_borrow.status_code == 403

        # 13e. home_id tampering in path vs session
        tamper_bill = await client.get(f"/api/v1/homes/{home_id}/bills/{bill_id}", headers=headers_x)
        assert tamper_bill.status_code == 403
