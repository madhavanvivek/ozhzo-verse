import pytest
from datetime import date, datetime, time, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_phase6_calendar_complete_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Users & Homes
        # User A1 (Home Owner / Admin)
        u_a1 = await client.post("/api/v1/auth/register", json={
            "email": "vivek_cal@ozhzo.com",
            "password": "Password123!",
            "full_name": "Vivek Madhavan"
        })
        token_a1 = u_a1.json()["data"]["tokens"]["access_token"]
        user_a1_id = u_a1.json()["data"]["tokens"]["user_id"]
        headers_a1 = {"Authorization": f"Bearer {token_a1}"}

        # User A2 (Home Member)
        u_a2 = await client.post("/api/v1/auth/register", json={
            "email": "karthika_cal@ozhzo.com",
            "password": "Password123!",
            "full_name": "Karthika Vivek"
        })
        token_a2 = u_a2.json()["data"]["tokens"]["access_token"]
        user_a2_id = u_a2.json()["data"]["tokens"]["user_id"]
        headers_a2 = {"Authorization": f"Bearer {token_a2}"}

        # User B (Different Home Owner)
        u_b = await client.post("/api/v1/auth/register", json={
            "email": "external_user_cal@ozhzo.com",
            "password": "Password123!",
            "full_name": "External User"
        })
        token_b = u_b.json()["data"]["tokens"]["access_token"]
        user_b_id = u_b.json()["data"]["tokens"]["user_id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Home A & Home B
        home_a_res = await client.post("/api/v1/homes", json={"name": "Madhavan Home Calendar", "timezone": "Asia/Kolkata"}, headers=headers_a1)
        home_a_id = home_a_res.json()["data"]["id"]

        home_b_res = await client.post("/api/v1/homes", json={"name": "External Home Calendar", "timezone": "America/New_York"}, headers=headers_b)
        home_b_id = home_b_res.json()["data"]["id"]

        # Add User A2 as active member of Home A
        inv_res = await client.post(f"/api/v1/homes/{home_a_id}/members", json={
            "email": "karthika_cal@ozhzo.com",
            "role": "MEMBER"
        }, headers=headers_a1)
        assert inv_res.status_code == 201

        # -------------------------------------------------------------
        # 1. Event Category CRUD
        # -------------------------------------------------------------
        cat_res = await client.post(f"/api/v1/homes/{home_a_id}/events/categories", json={
            "name": "Family Gatherings",
            "icon": "users",
            "color": "#4f46e5"
        }, headers=headers_a1)
        assert cat_res.status_code == 201
        cat_id = cat_res.json()["data"]["id"]

        # Duplicate category in same home rejected
        dup_cat = await client.post(f"/api/v1/homes/{home_a_id}/events/categories", json={
            "name": "Family Gatherings"
        }, headers=headers_a1)
        assert dup_cat.status_code == 400

        # List categories
        list_cats = await client.get(f"/api/v1/homes/{home_a_id}/events/categories", headers=headers_a1)
        assert list_cats.status_code == 200
        assert len(list_cats.json()["data"]) >= 1

        # -------------------------------------------------------------
        # 2. Quick Timed Event Creation
        # -------------------------------------------------------------
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        create_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Doctor Appointment",
            "description": "Annual pediatric checkup",
            "location": "City Clinic Room 4",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "is_all_day": False,
            "category_id": cat_id,
            "participant_user_ids": [user_a2_id]
        }, headers=headers_a1)
        assert create_res.status_code == 201
        doc_event = create_res.json()["data"]
        doc_event_id = doc_event["id"]
        assert doc_event["title"] == "Doctor Appointment"
        assert doc_event["category_name"] == "Family Gatherings"
        assert len(doc_event["participants"]) == 1
        assert doc_event["participants"][0]["user_id"] == user_a2_id
        assert doc_event["participants"][0]["status"] == "INVITED"

        # -------------------------------------------------------------
        # 3. All-Day Event & Multi-Day Trip
        # -------------------------------------------------------------
        bday_start = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        bday_end = (now + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=0)

        bday_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Grandmother's 80th Birthday",
            "start_time": bday_start.isoformat(),
            "end_time": bday_end.isoformat(),
            "is_all_day": True
        }, headers=headers_a1)
        assert bday_res.status_code == 201
        assert bday_res.json()["data"]["is_all_day"] is True

        # Multi-day trip
        trip_start = (now + timedelta(days=5)).replace(hour=8, minute=0, second=0, microsecond=0)
        trip_end = (now + timedelta(days=8)).replace(hour=20, minute=0, second=0, microsecond=0)
        trip_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Mysore Weekend Road Trip",
            "location": "Mysore Heritage Resort",
            "start_time": trip_start.isoformat(),
            "end_time": trip_end.isoformat(),
            "is_all_day": True
        }, headers=headers_a1)
        assert trip_res.status_code == 201

        # -------------------------------------------------------------
        # 4. Invalid Participant (Cross-Home & Non-Existent)
        # -------------------------------------------------------------
        cross_part_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Private Event",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "participant_user_ids": [user_b_id]
        }, headers=headers_a1)
        assert cross_part_res.status_code == 400
        assert "All participants must be active members" in cross_part_res.json()["detail"]

        # -------------------------------------------------------------
        # 5. Validation: End Before Start Rejection
        # -------------------------------------------------------------
        invalid_time_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Time Paradox Meeting",
            "start_time": end_time.isoformat(),
            "end_time": start_time.isoformat()
        }, headers=headers_a1)
        assert invalid_time_res.status_code == 422

        # -------------------------------------------------------------
        # 6. Participant RSVP Status Update
        # -------------------------------------------------------------
        rsvp_res = await client.post(f"/api/v1/homes/{home_a_id}/events/{doc_event_id}/participants/{user_a2_id}/status", json={
            "status": "ACCEPTED"
        }, headers=headers_a2)
        assert rsvp_res.status_code == 200

        # Verify RSVP reflected
        get_evt = await client.get(f"/api/v1/homes/{home_a_id}/events/{doc_event_id}", headers=headers_a1)
        assert get_evt.status_code == 200
        assert get_evt.json()["data"]["participants"][0]["status"] == "ACCEPTED"

        # -------------------------------------------------------------
        # 7. Event Edit & Optimistic Locking Concurrency
        # -------------------------------------------------------------
        v = get_evt.json()["data"]["version"]
        conflict_edit = await client.patch(f"/api/v1/homes/{home_a_id}/events/{doc_event_id}", json={
            "title": "Stale Edit",
            "version": v + 99
        }, headers=headers_a1)
        assert conflict_edit.status_code == 409

        valid_edit = await client.patch(f"/api/v1/homes/{home_a_id}/events/{doc_event_id}", json={
            "location": "City Clinic Room 4B (Updated)",
            "version": v
        }, headers=headers_a1)
        assert valid_edit.status_code == 200
        assert valid_edit.json()["data"]["location"] == "City Clinic Room 4B (Updated)"
        assert valid_edit.json()["data"]["version"] == v + 1

        # -------------------------------------------------------------
        # 8. Event Soft-Delete / Cancellation
        # -------------------------------------------------------------
        cancel_res = await client.delete(f"/api/v1/homes/{home_a_id}/events/{doc_event_id}", headers=headers_a1)
        assert cancel_res.status_code == 200

        # Cancelled event no longer in default active list
        list_active = await client.get(f"/api/v1/homes/{home_a_id}/events", headers=headers_a1)
        active_ids = [e["id"] for e in list_active.json()["data"]]
        assert doc_event_id not in active_ids

        # -------------------------------------------------------------
        # 9. Recurring Event Schedule
        # -------------------------------------------------------------
        recur_res = await client.post(f"/api/v1/homes/{home_a_id}/events", json={
            "title": "Weekly Family Call",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "recurrence_type": "WEEKLY"
        }, headers=headers_a1)
        assert recur_res.status_code == 201
        assert recur_res.json()["data"]["recurrence_type"] == "WEEKLY"

        # -------------------------------------------------------------
        # 10. Multi-Home Security Isolation (Cross-Home 403)
        # -------------------------------------------------------------
        cross_view = await client.get(f"/api/v1/homes/{home_a_id}/events", headers=headers_b)
        assert cross_view.status_code == 403

        # -------------------------------------------------------------
        # 11. Create Task & Bill in Home A (For Projection Verification)
        # -------------------------------------------------------------
        task_due = (date.today() + timedelta(days=2)).isoformat()
        t_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Replace RO Water Filter",
            "due_date": task_due,
            "priority": "NORMAL"
        }, headers=headers_a1)
        assert t_res.status_code == 201
        task_id = t_res.json()["data"]["id"]

        bill_due = (date.today() + timedelta(days=3)).isoformat()
        b_res = await client.post(f"/api/v1/homes/{home_a_id}/bills", json={
            "title": "Airtel Fiber Internet",
            "expected_amount": "999.00",
            "due_date": bill_due
        }, headers=headers_a1)
        assert b_res.status_code == 201
        bill_id = b_res.json()["data"]["id"]

        # -------------------------------------------------------------
        # 12. Dynamic Unified Calendar Projection
        # -------------------------------------------------------------
        proj_start = (now - timedelta(days=1)).isoformat()
        proj_end = (now + timedelta(days=10)).isoformat()

        proj_res = await client.get(
            f"/api/v1/homes/{home_a_id}/calendar/projection?start_date={proj_start}&end_date={proj_end}",
            headers=headers_a1
        )
        assert proj_res.status_code == 200
        proj_data = proj_res.json()["data"]

        items = proj_data["items"]
        assert len(items) >= 3

        # Verify source_type discrimination
        event_items = [i for i in items if i["source_type"] == "EVENT"]
        task_items = [i for i in items if i["source_type"] == "TASK"]
        bill_items = [i for i in items if i["source_type"] == "BILL"]

        assert len(event_items) >= 2  # Birthday and Trip (Doctor Appointment was cancelled)
        assert len(task_items) >= 1
        assert len(bill_items) >= 1

        # Check Task projection fields
        projected_task = next(i for i in task_items if i["source_id"] == task_id)
        assert projected_task["editable"] is False
        assert projected_task["navigation_target"] == f"/tasks/{task_id}"
        assert "Replace RO Water Filter" in projected_task["title"]

        # Check Bill projection fields
        projected_bill = next(i for i in bill_items if i["source_id"] == bill_id)
        assert projected_bill["editable"] is False
        assert projected_bill["navigation_target"] == f"/bills/{bill_id}"
        assert "Airtel Fiber Internet" in projected_bill["title"]

        # -------------------------------------------------------------
        # 13. Zero Data Duplication Assertion
        # -------------------------------------------------------------
        # Assert tasks and bills NEVER created rows in `events` table
        all_events_res = await client.get(f"/api/v1/homes/{home_a_id}/events", headers=headers_a1)
        all_event_titles = [e["title"] for e in all_events_res.json()["data"]]
        assert "Replace RO Water Filter" not in all_event_titles
        assert "Airtel Fiber Internet" not in all_event_titles
