import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_phase4_tasks_complete_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Users & Homes
        # User A1 (Home Owner / Admin)
        u_a1 = await client.post("/api/v1/auth/register", json={
            "email": "vivek_task@ozhzo.com",
            "password": "Password123!",
            "full_name": "Vivek Madhavan"
        })
        token_a1 = u_a1.json()["data"]["tokens"]["access_token"]
        user_a1_id = u_a1.json()["data"]["tokens"]["user_id"]
        headers_a1 = {"Authorization": f"Bearer {token_a1}"}

        # User A2 (Home Member)
        u_a2 = await client.post("/api/v1/auth/register", json={
            "email": "karthika_task@ozhzo.com",
            "password": "Password123!",
            "full_name": "Karthika Vivek"
        })
        token_a2 = u_a2.json()["data"]["tokens"]["access_token"]
        user_a2_id = u_a2.json()["data"]["tokens"]["user_id"]
        headers_a2 = {"Authorization": f"Bearer {token_a2}"}

        # User B (Different Home Owner)
        u_b = await client.post("/api/v1/auth/register", json={
            "email": "external_user_task@ozhzo.com",
            "password": "Password123!",
            "full_name": "External User"
        })
        token_b = u_b.json()["data"]["tokens"]["access_token"]
        user_b_id = u_b.json()["data"]["tokens"]["user_id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Home A & Home B
        home_a_res = await client.post("/api/v1/homes", json={"name": "Madhavan Home Tasks"}, headers=headers_a1)
        home_a_id = home_a_res.json()["data"]["id"]

        home_b_res = await client.post("/api/v1/homes", json={"name": "External Home Tasks"}, headers=headers_b)
        home_b_id = home_b_res.json()["data"]["id"]

        # Add User A2 as active member of Home A
        inv_res = await client.post(f"/api/v1/homes/{home_a_id}/members", json={
            "email": "karthika_task@ozhzo.com",
            "role": "MEMBER"
        }, headers=headers_a1)
        assert inv_res.status_code == 201

        # -------------------------------------------------------------
        # 1. Global Task Templates Catalog
        # -------------------------------------------------------------
        tpl_res = await client.get("/api/v1/task-templates", headers=headers_a1)
        assert tpl_res.status_code == 200
        templates = tpl_res.json()["data"]
        assert len(templates) >= 8
        filter_tpl = next(t for t in templates if t["name"] == "Clean Water Filter")
        assert filter_tpl["default_interval_days"] == 30
        assert filter_tpl["default_recurrence_type"] == "CUSTOM_DAYS"

        # -------------------------------------------------------------
        # 2. Task Category Creation
        # -------------------------------------------------------------
        cat_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks/categories", json={
            "name": "Maintenance & Repair",
            "icon": "wrench",
            "color": "#3b82f6"
        }, headers=headers_a1)
        assert cat_res.status_code == 201
        category_id = cat_res.json()["data"]["id"]

        # -------------------------------------------------------------
        # 3. Quick Add Task (Title only mandatory)
        # -------------------------------------------------------------
        quick_task_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Mop kitchen floor"
        }, headers=headers_a1)
        assert quick_task_res.status_code == 201
        quick_task = quick_task_res.json()["data"]
        assert quick_task["title"] == "Mop kitchen floor"
        assert quick_task["priority"] == "NORMAL"
        assert quick_task["status"] == "TODO"
        assert quick_task["assigned_to"] is None
        assert quick_task["due_date"] is None
        assert quick_task["version"] == 1

        # -------------------------------------------------------------
        # 4. Detailed Task Creation with Template & Category
        # -------------------------------------------------------------
        now = datetime.now(timezone.utc)
        due_tomorrow = now + timedelta(days=1)

        det_task_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "template_id": filter_tpl["id"],
            "category_id": category_id,
            "title": "Clean RO Water Filter",
            "description": "Replace 5-micron spun candle and sanitize pre-filter bowl",
            "priority": "HIGH",
            "assigned_to": user_a2_id,
            "due_date": due_tomorrow.isoformat(),
            "recurrence_type": "CUSTOM_DAYS",
            "recurrence_interval_days": 30,
            "recurrence_strategy": "COMPLETION_DATE"
        }, headers=headers_a1)
        assert det_task_res.status_code == 201
        det_task = det_task_res.json()["data"]
        assert det_task["title"] == "Clean RO Water Filter"
        assert det_task["category_name"] == "Maintenance & Repair"
        assert det_task["assigned_to_name"] == "Karthika Vivek"
        assert det_task["priority"] == "HIGH"
        assert det_task["recurrence_strategy"] == "COMPLETION_DATE"
        ro_task_id = det_task["id"]

        # -------------------------------------------------------------
        # 5. Assignment Security (Reject non-members / cross-home members)
        # -------------------------------------------------------------
        # Attempt to assign Home A task to User B (not in Home A) -> Blocked 400
        invalid_assign_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Invalid Assigned Task",
            "assigned_to": user_b_id
        }, headers=headers_a1)
        assert invalid_assign_res.status_code == 400

        # -------------------------------------------------------------
        # 6. Task Assignment & Unassignment Action
        # -------------------------------------------------------------
        # Reassign quick task to User A1
        assign_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks/{quick_task['id']}/assign", json={
            "assigned_to": user_a1_id
        }, headers=headers_a1)
        assert assign_res.status_code == 200
        assert assign_res.json()["data"]["assigned_to"] == user_a1_id
        assert assign_res.json()["data"]["version"] == 2

        # Unassign task
        unassign_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks/{quick_task['id']}/assign", json={
            "assigned_to": None
        }, headers=headers_a1)
        assert unassign_res.status_code == 200
        assert unassign_res.json()["data"]["assigned_to"] is None

        # -------------------------------------------------------------
        # 7. Time State Derivations (Overdue, Due Today, Upcoming)
        # -------------------------------------------------------------
        # Create an overdue task (due 2 days ago)
        overdue_date = now - timedelta(days=2)
        overdue_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Pay Electricity Bill",
            "due_date": overdue_date.isoformat(),
            "priority": "HIGH"
        }, headers=headers_a1)
        assert overdue_res.status_code == 201
        assert overdue_res.json()["data"]["is_overdue"] is True
        assert overdue_res.json()["data"]["is_due_today"] is False
        overdue_task_id = overdue_res.json()["data"]["id"]

        # Create a due today task
        today_date = now + timedelta(hours=2)
        today_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks", json={
            "title": "Take out recycling bin",
            "due_date": today_date.isoformat(),
            "assigned_to": user_a2_id
        }, headers=headers_a1)
        assert today_res.status_code == 201
        assert today_res.json()["data"]["is_due_today"] is True
        today_task_id = today_res.json()["data"]["id"]

        # -------------------------------------------------------------
        # 8. Dynamic Views & Filtering
        # -------------------------------------------------------------
        # Query view=overdue
        v_overdue = await client.get(f"/api/v1/homes/{home_a_id}/tasks?view=overdue", headers=headers_a1)
        assert v_overdue.status_code == 200
        assert any(t["id"] == overdue_task_id for t in v_overdue.json()["data"]["items"])

        # Query view=today
        v_today = await client.get(f"/api/v1/homes/{home_a_id}/tasks?view=today", headers=headers_a1)
        assert v_today.status_code == 200
        assert any(t["id"] == today_task_id for t in v_today.json()["data"]["items"])

        # Query view=my_tasks as User A2 (Karthika)
        v_my = await client.get(f"/api/v1/homes/{home_a_id}/tasks?view=my_tasks", headers=headers_a2)
        assert v_my.status_code == 200
        my_items = v_my.json()["data"]["items"]
        assert all(t["assigned_to"] == user_a2_id for t in my_items)
        assert any(t["id"] == ro_task_id for t in my_items)

        # -------------------------------------------------------------
        # 9. Summary KPIs Endpoint
        # -------------------------------------------------------------
        summary_res = await client.get(f"/api/v1/homes/{home_a_id}/tasks/summary", headers=headers_a1)
        assert summary_res.status_code == 200
        sum_data = summary_res.json()["data"]
        assert sum_data["total_active"] >= 4
        assert sum_data["due_today"] >= 1
        assert sum_data["overdue"] >= 1
        assert sum_data["upcoming"] >= 1

        # -------------------------------------------------------------
        # 10. Optimistic Concurrency Locking on Edit
        # -------------------------------------------------------------
        # Mismatched version -> 409 Conflict
        conf_res = await client.patch(f"/api/v1/homes/{home_a_id}/tasks/{ro_task_id}", json={
            "title": "Conflicting Edit",
            "version": 999
        }, headers=headers_a1)
        assert conf_res.status_code == 409

        # Correct version -> 200 OK
        ok_edit_res = await client.patch(f"/api/v1/homes/{home_a_id}/tasks/{ro_task_id}", json={
            "description": "Updated filter notes",
            "version": det_task["version"]
        }, headers=headers_a1)
        assert ok_edit_res.status_code == 200
        assert ok_edit_res.json()["data"]["description"] == "Updated filter notes"
        assert ok_edit_res.json()["data"]["version"] == det_task["version"] + 1

        # -------------------------------------------------------------
        # 11. Recurring Task Completion & Atomic Next Occurrence Spawning
        # -------------------------------------------------------------
        # Karthika completes "Clean RO Water Filter" (CUSTOM_DAYS, 30 days, COMPLETION_DATE)
        current_v = ok_edit_res.json()["data"]["version"]
        comp_res = await client.post(f"/api/v1/homes/{home_a_id}/tasks/{ro_task_id}/complete", json={
            "notes": "Done using 5 micron candle",
            "version": current_v
        }, headers=headers_a2)
        assert comp_res.status_code == 200
        comp_data = comp_res.json()["data"]
        assert comp_data["status"] == "COMPLETED"
        assert comp_data["completed_by"] == user_a2_id
        assert comp_data["completed_by_name"] == "Karthika Vivek"

        # Verify next occurrence was automatically scheduled ~30 days from now
        list_active_res = await client.get(f"/api/v1/homes/{home_a_id}/tasks?status=TODO", headers=headers_a1)
        active_items = list_active_res.json()["data"]["items"]
        next_occurrence = next((t for t in active_items if t["title"] == "Clean RO Water Filter" and t["id"] != ro_task_id), None)
        assert next_occurrence is not None
        assert next_occurrence["status"] == "TODO"
        assert next_occurrence["parent_recurring_task_id"] == ro_task_id
        # Due date should be ~30 days in future
        next_due_dt = datetime.fromisoformat(next_occurrence["due_date"].replace("Z", "+00:00"))
        assert (next_due_dt - now).days >= 29

        # Verify Double Completion is Blocked (HTTP 400)
        double_comp = await client.post(f"/api/v1/homes/{home_a_id}/tasks/{ro_task_id}/complete", json={}, headers=headers_a2)
        assert double_comp.status_code == 400

        # -------------------------------------------------------------
        # 12. Completed History View
        # -------------------------------------------------------------
        hist_res = await client.get(f"/api/v1/homes/{home_a_id}/tasks?view=completed", headers=headers_a1)
        assert hist_res.status_code == 200
        history_tasks = hist_res.json()["data"]["items"]
        assert any(t["id"] == ro_task_id and t["status"] == "COMPLETED" for t in history_tasks)

        # -------------------------------------------------------------
        # 13. Soft Deletion / Cancellation
        # -------------------------------------------------------------
        del_res = await client.delete(f"/api/v1/homes/{home_a_id}/tasks/{quick_task['id']}", headers=headers_a1)
        assert del_res.status_code == 200

        # Deleted task no longer appears in active list
        active_after_del = await client.get(f"/api/v1/homes/{home_a_id}/tasks?status=TODO", headers=headers_a1)
        assert not any(t["id"] == quick_task["id"] for t in active_after_del.json()["data"]["items"])

        # -------------------------------------------------------------
        # 14. Multi-Home Security Isolation
        # -------------------------------------------------------------
        # User B (Home B) tries to read Home A tasks -> 403 Forbidden
        cross_read = await client.get(f"/api/v1/homes/{home_a_id}/tasks", headers=headers_b)
        assert cross_read.status_code == 403

        # User B tries to complete Home A task -> 403 Forbidden
        cross_comp = await client.post(f"/api/v1/homes/{home_a_id}/tasks/{ro_task_id}/complete", json={}, headers=headers_b)
        assert cross_comp.status_code == 403

        # User B tries to delete Home A task -> 403 Forbidden
        cross_del = await client.delete(f"/api/v1/homes/{home_a_id}/tasks/{ro_task_id}", headers=headers_b)
        assert cross_del.status_code == 403
