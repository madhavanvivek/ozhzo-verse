import pytest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_phase7_integration_complete_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Users & Multi-Home Environment
        # User A1 (Home Owner)
        u_a1 = await client.post("/api/v1/auth/register", json={
            "email": "owner_p7@ozhzo.com",
            "password": "Password123!",
            "full_name": "Vivek Madhavan"
        })
        token_a1 = u_a1.json()["data"]["tokens"]["access_token"]
        user_a1_id = u_a1.json()["data"]["tokens"]["user_id"]
        headers_a1 = {"Authorization": f"Bearer {token_a1}"}

        # User A2 (Home Member)
        u_a2 = await client.post("/api/v1/auth/register", json={
            "email": "member_p7@ozhzo.com",
            "password": "Password123!",
            "full_name": "Karthika Vivek"
        })
        token_a2 = u_a2.json()["data"]["tokens"]["access_token"]
        user_a2_id = u_a2.json()["data"]["tokens"]["user_id"]
        headers_a2 = {"Authorization": f"Bearer {token_a2}"}

        # User B (External Home Owner)
        u_b = await client.post("/api/v1/auth/register", json={
            "email": "external_p7@ozhzo.com",
            "password": "Password123!",
            "full_name": "External User"
        })
        token_b = u_b.json()["data"]["tokens"]["access_token"]
        user_b_id = u_b.json()["data"]["tokens"]["user_id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Home A & Home B
        h_a = await client.post("/api/v1/homes", json={"name": "Madhavan Home P7", "timezone": "Asia/Kolkata"}, headers=headers_a1)
        home_a_id = h_a.json()["data"]["id"]

        h_b = await client.post("/api/v1/homes", json={"name": "External Home P7", "timezone": "America/New_York"}, headers=headers_b)
        home_b_id = h_b.json()["data"]["id"]

        # Add User A2 as active member of Home A
        inv_res = await client.post(f"/api/v1/homes/{home_a_id}/members", json={
            "email": "member_p7@ozhzo.com",
            "role": "MEMBER"
        }, headers=headers_a1)
        assert inv_res.status_code == 201

        # -------------------------------------------------------------
        # 2. Seed Home A Domain Records
        # -------------------------------------------------------------
        today = date.today()
        now_utc = datetime.now(timezone.utc)

        # 2a. Location & Asset
        loc_res = await client.post(f"/api/v1/homes/{home_a_id}/locations", json={
            "name": "Garage Workshop",
            "location_type": "ROOM",
            "description": "Main tool storage"
        }, headers=headers_a1)
        assert loc_res.status_code == 201
        loc_id = loc_res.json()["data"]["id"]

        asset_res = await client.post(f"/api/v1/homes/{home_a_id}/inventory/items", json={
            "name": "Bosch Hammer Drill 800W",
            "item_type": "ASSET",
            "location_id": loc_id,
            "condition": "GOOD"
        }, headers=headers_a1)
        assert asset_res.status_code == 201
        asset_id = asset_res.json()["data"]["id"]

        # 2b. Consumable Inventory (Low & Out of Stock)
        rice_res = await client.post(f"/api/v1/homes/{home_a_id}/inventory/items", json={
            "name": "Basmati Rice Royal",
            "item_type": "CONSUMABLE",
            "quantity": 0,
            "unit": "kg",
            "min_threshold": 5,
            "location_id": loc_id
        }, headers=headers_a1)
        assert rice_res.status_code == 201
        rice_id = rice_res.json()["data"]["id"]

        # 2c. Purchase List Item
        pur_res = await client.post(f"/api/v1/homes/{home_a_id}/purchase-list/items", json={
            "name": "Organic Milk 2L",
            "quantity": 2,
            "unit": "L",
            "priority": "HIGH"
        }, headers=headers_a1)
        assert pur_res.status_code == 201
        pur_id = pur_res.json()["data"]["id"]

        # 2d. Tasks (Overdue & Due Today)
        overdue_task_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Clean Water Filter Cartridge",
            "priority": "HIGH",
            "due_date": (today - timedelta(days=2)).isoformat(),
            "assigned_to": user_a2_id
        }, headers=headers_a1)
        assert overdue_task_res.status_code == 201
        overdue_task_id = overdue_task_res.json()["data"]["id"]

        today_task_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Take Out Recycling Bin",
            "priority": "NORMAL",
            "due_date": today.isoformat()
        }, headers=headers_a1)
        assert today_task_res.status_code == 201
        today_task_id = today_task_res.json()["data"]["id"]

        # 2e. Bills (Overdue & Due Today)
        overdue_bill_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "BESCOM Electricity Bill",
            "expected_amount": "2137.00",
            "due_date": (today - timedelta(days=3)).isoformat()
        }, headers=headers_a1)
        assert overdue_bill_res.status_code == 201
        overdue_bill_id = overdue_bill_res.json()["data"]["id"]

        today_bill_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Airtel High Speed Fiber",
            "expected_amount": "999.00",
            "due_date": today.isoformat()
        }, headers=headers_a1)
        assert today_bill_res.status_code == 201
        today_bill_id = today_bill_res.json()["data"]["id"]

        # 2f. Calendar Event Today
        event_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Family Doctor Appointment",
            "start_time": (now_utc + timedelta(hours=1)).isoformat(),
            "end_time": (now_utc + timedelta(hours=2)).isoformat(),
            "location": "City Clinic Room 4"
        }, headers=headers_a1)
        assert event_res.status_code == 201
        event_id = event_res.json()["data"]["id"]

        # -------------------------------------------------------------
        # 3. Test Attention Center (Ranking & Categories)
        # -------------------------------------------------------------
        att_res = await client.get(f"/api/v1/homes/{home_a_id}/attention", headers=headers_a1)
        assert att_res.status_code == 200
        att_data = att_res.json()["data"]

        summary = att_data["summary"]
        assert summary["critical_count"] >= 2  # Overdue Bill + Overdue Task
        assert summary["high_count"] >= 3      # Bill Due Today + Task Due Today + Out of Stock Rice
        assert summary["total_attention_items"] >= 5

        categories = [item["category"] for item in att_data["items"]]
        assert "BILL_OVERDUE" in categories
        assert "TASK_OVERDUE" in categories
        assert "BILL_DUE_TODAY" in categories
        assert "TASK_DUE_TODAY" in categories
        assert "STOCK_EMPTY" in categories

        # -------------------------------------------------------------
        # 4. Test Unified Today View (Projections)
        # -------------------------------------------------------------
        today_res = await client.get(f"/api/v1/homes/{home_a_id}/today", headers=headers_a1)
        assert today_res.status_code == 200
        today_data = today_res.json()["data"]

        assert today_data["date"] == today.isoformat()
        timeline = today_data["timeline"]
        source_types = [item["source_type"] for item in timeline]
        assert "EVENT" in source_types
        assert "TASK" in source_types
        assert "BILL" in source_types

        # Verify Attention Alerts in Today View
        alerts = today_data["attention_alerts"]
        alert_sources = [a["source_type"] for a in alerts]
        assert "INVENTORY" in alert_sources
        assert "PURCHASE" in alert_sources

        # -------------------------------------------------------------
        # 5. Test Global Search & Home Memory (8 Domains)
        # -------------------------------------------------------------
        # 5a. Search Asset
        search_drill = await client.get(f"/api/v1/homes/{home_a_id}/search?q=drill", headers=headers_a1)
        assert search_drill.status_code == 200
        items = search_drill.json()["data"]["items"]
        assert len(items) >= 1
        assert items[0]["domain"] == "ASSET"
        assert "Bosch Hammer Drill" in items[0]["title"]
        assert "Garage Workshop" in items[0]["location_path"]

        # 5b. Search Bill
        search_elec = await client.get(f"/api/v1/homes/{home_a_id}/search?q=electricity", headers=headers_a1)
        assert search_elec.status_code == 200
        bill_items = search_elec.json()["data"]["items"]
        assert len(bill_items) >= 1
        assert bill_items[0]["domain"] == "BILL"
        assert "2137.00" in bill_items[0]["subtitle"]

        # 5c. Search Task
        search_task = await client.get(f"/api/v1/homes/{home_a_id}/search?q=filter", headers=headers_a1)
        assert search_task.status_code == 200
        task_items = search_task.json()["data"]["items"]
        assert len(task_items) >= 1
        assert task_items[0]["domain"] == "TASK"

        # 5d. Search Member
        search_mem = await client.get(f"/api/v1/homes/{home_a_id}/search?q=karthika", headers=headers_a1)
        assert search_mem.status_code == 200
        mem_items = search_mem.json()["data"]["items"]
        assert len(mem_items) >= 1
        assert mem_items[0]["domain"] == "MEMBER"

        # -------------------------------------------------------------
        # 6. Test Home Activity Feed
        # -------------------------------------------------------------
        act_res = await client.get(f"/api/v1/homes/{home_a_id}/activity", headers=headers_a1)
        assert act_res.status_code == 200
        assert "items" in act_res.json()["data"]

        # -------------------------------------------------------------
        # 7. Test Home Dashboard Aggregator
        # -------------------------------------------------------------
        dash_res = await client.get(f"/api/v1/homes/{home_a_id}/dashboard", headers=headers_a1)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()["data"]

        assert dash_data["greeting"]["user_display_name"] == "Vivek Madhavan"
        assert dash_data["summary"]["home_name"] == "Madhavan Home P7"
        assert dash_data["summary"]["members_count"] == 2
        assert len(dash_data["attention_items"]) >= 2
        assert len(dash_data["today_timeline"]) >= 2

        # -------------------------------------------------------------
        # 8. Test Multi-Home Isolation & Cross-Home Search Leakage Block
        # -------------------------------------------------------------
        # User B in Home B searches for Home A's unique asset "Bosch"
        b_search = await client.get(f"/api/v1/homes/{home_b_id}/search?q=Bosch", headers=headers_b)
        assert b_search.status_code == 200
        assert len(b_search.json()["data"]["items"]) == 0

        # User B cannot access Home A dashboard or attention
        cross_dash = await client.get(f"/api/v1/homes/{home_a_id}/dashboard", headers=headers_b)
        assert cross_dash.status_code == 403

        cross_att = await client.get(f"/api/v1/homes/{home_a_id}/attention", headers=headers_b)
        assert cross_att.status_code == 403

        cross_today = await client.get(f"/api/v1/homes/{home_a_id}/today", headers=headers_b)
        assert cross_today.status_code == 403
