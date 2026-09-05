import pytest
from datetime import date, datetime, time, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func
from src.main import app
from src.infrastructure.database.models import EventModel
from src.infrastructure.database.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_courses_calendar_projection_comprehensive():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Users & Homes
        u_a = await client.post("/api/v1/auth/register", json={
            "email": "course_parent@ozhzo.com",
            "password": "Password123!",
            "full_name": "Course Parent"
        })
        token_a = u_a.json()["data"]["tokens"]["access_token"]
        user_a_id = u_a.json()["data"]["tokens"]["user_id"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        u_b = await client.post("/api/v1/auth/register", json={
            "email": "course_neighbor@ozhzo.com",
            "password": "Password123!",
            "full_name": "Course Neighbor"
        })
        token_b = u_b.json()["data"]["tokens"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Home A & Home B
        home_a_res = await client.post("/api/v1/homes", json={"name": "Family Learning Home A", "timezone": "UTC"}, headers=headers_a)
        home_a_id = home_a_res.json()["data"]["id"]

        home_b_res = await client.post("/api/v1/homes", json={"name": "Neighbor Home B", "timezone": "UTC"}, headers=headers_b)
        home_b_id = home_b_res.json()["data"]["id"]

        # -------------------------------------------------------------
        # 2. Course CRUD
        # -------------------------------------------------------------
        now = datetime.now(timezone.utc)
        start_date = now.date()
        end_date = start_date + timedelta(days=90)

        course_res = await client.post(f"/api/v1/homes/{home_a_id}/courses", json={
            "title": "Python Programming Masterclass",
            "description": "Comprehensive Python bootcamp for kids and teens",
            "instructor": "Dr. Angela Yu",
            "provider": "Codecademy / Coursera",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "status": "ACTIVE",
            "color": "#6366f1"
        }, headers=headers_a)
        assert course_res.status_code == 201
        course = course_res.json()["data"]
        course_id = course["id"]
        assert course["title"] == "Python Programming Masterclass"

        # List courses
        courses_list = await client.get(f"/api/v1/homes/{home_a_id}/courses", headers=headers_a)
        assert courses_list.status_code == 200
        assert len(courses_list.json()["data"]) >= 1

        # -------------------------------------------------------------
        # 3. Course Session Creation & Date Shifting
        # -------------------------------------------------------------
        sess_start = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        sess_end = sess_start + timedelta(hours=2)

        sess_res = await client.post(f"/api/v1/homes/{home_a_id}/courses/{course_id}/sessions", json={
            "title": "Live Coding: Functions and Loops",
            "start_time": sess_start.isoformat(),
            "end_time": sess_end.isoformat(),
            "is_all_day": False,
            "location": "Zoom Room / Study Desk",
            "recurrence_type": "WEEKLY",
            "notes": "Bring textbook chapter 4",
            "status": "SCHEDULED"
        }, headers=headers_a)
        assert sess_res.status_code == 201
        session = sess_res.json()["data"]
        session_id = session["id"]
        assert session["title"] == "Live Coding: Functions and Loops"

        # -------------------------------------------------------------
        # 4. Course Assignment Creation
        # -------------------------------------------------------------
        assign_due = (now + timedelta(days=5)).date()
        assign_res = await client.post(f"/api/v1/homes/{home_a_id}/courses/{course_id}/assignments", json={
            "title": "Build Calculator App",
            "description": "Implement basic arithmetic operations with unit tests",
            "due_date": assign_due.isoformat(),
            "status": "PENDING"
        }, headers=headers_a)
        assert assign_res.status_code == 201
        assignment = assign_res.json()["data"]
        assign_id = assignment["id"]
        assert assignment["title"] == "Build Calculator App"

        # -------------------------------------------------------------
        # 5. Course Exam Creation
        # -------------------------------------------------------------
        exam_start = (now + timedelta(days=14)).replace(hour=14, minute=0, second=0, microsecond=0)
        exam_end = exam_start + timedelta(hours=3)
        exam_res = await client.post(f"/api/v1/homes/{home_a_id}/courses/{course_id}/exams", json={
            "title": "Midterm Practical Exam",
            "start_time": exam_start.isoformat(),
            "end_time": exam_end.isoformat(),
            "location": "Online Portal",
            "notes": "Timed 180-minute exam",
            "status": "SCHEDULED"
        }, headers=headers_a)
        assert exam_res.status_code == 201
        exam = exam_res.json()["data"]
        exam_id = exam["id"]
        assert exam["title"] == "Midterm Practical Exam"

        # -------------------------------------------------------------
        # 6. Verify Unified Calendar Projection
        # -------------------------------------------------------------
        proj_start = now - timedelta(days=1)
        proj_end = now + timedelta(days=30)
        proj_res = await client.get(
            f"/api/v1/homes/{home_a_id}/calendar/projection?start_date={proj_start.isoformat()}&end_date={proj_end.isoformat()}&include_courses=true",
            headers=headers_a
        )
        assert proj_res.status_code == 200
        proj_data = proj_res.json()["data"]
        assert proj_data["total_courses"] >= 3

        course_items = [item for item in proj_data["items"] if item["source_type"] == "COURSE"]
        assert len(course_items) == 3

        session_proj = next((i for i in course_items if i["meta_info"]["subtype"] == "SESSION"), None)
        assert session_proj is not None
        assert "Functions and Loops" in session_proj["title"]
        assert session_proj["status"] == "SCHEDULED"

        assign_proj = next((i for i in course_items if i["meta_info"]["subtype"] == "ASSIGNMENT"), None)
        assert assign_proj is not None
        assert "Build Calculator App" in assign_proj["title"]
        assert assign_proj["status"] == "PENDING"

        exam_proj = next((i for i in course_items if i["meta_info"]["subtype"] == "EXAM"), None)
        assert exam_proj is not None
        assert "Midterm Practical Exam" in exam_proj["title"]
        assert exam_proj["status"] == "SCHEDULED"

        # -------------------------------------------------------------
        # 7. Dynamic Synchronizations (Date Shift & Status Toggle)
        # -------------------------------------------------------------
        # Shift session date forward by 3 days
        new_sess_start = sess_start + timedelta(days=3)
        new_sess_end = sess_end + timedelta(days=3)
        patch_sess = await client.patch(
            f"/api/v1/homes/{home_a_id}/courses/{course_id}/sessions/{session_id}",
            json={
                "start_time": new_sess_start.isoformat(),
                "end_time": new_sess_end.isoformat(),
                "status": "ATTENDED"
            },
            headers=headers_a
        )
        assert patch_sess.status_code == 200

        # Mark assignment completed
        patch_assign = await client.patch(
            f"/api/v1/homes/{home_a_id}/courses/{course_id}/assignments/{assign_id}",
            json={"status": "COMPLETED"},
            headers=headers_a
        )
        assert patch_assign.status_code == 200

        # Re-fetch projection and verify live reflection
        proj_res2 = await client.get(
            f"/api/v1/homes/{home_a_id}/calendar/projection?start_date={proj_start.isoformat()}&end_date={proj_end.isoformat()}&include_courses=true",
            headers=headers_a
        )
        proj_data2 = proj_res2.json()["data"]
        course_items2 = [item for item in proj_data2["items"] if item["source_type"] == "COURSE"]

        session_proj2 = next((i for i in course_items2 if i["meta_info"]["subtype"] == "SESSION"), None)
        assert session_proj2["status"] == "ATTENDED"
        assert session_proj2["start"].startswith(new_sess_start.date().isoformat())

        assign_proj2 = next((i for i in course_items2 if i["meta_info"]["subtype"] == "ASSIGNMENT"), None)
        assert assign_proj2["status"] == "COMPLETED"
        assert assign_proj2["meta_info"]["is_completed"] is True

        # -------------------------------------------------------------
        # 8. Multi-Home Tenant Isolation
        # -------------------------------------------------------------
        # Home B calendar projection must have ZERO course items from Home A
        proj_b = await client.get(
            f"/api/v1/homes/{home_b_id}/calendar/projection?start_date={proj_start.isoformat()}&end_date={proj_end.isoformat()}&include_courses=true",
            headers=headers_b
        )
        assert proj_b.status_code == 200
        proj_b_data = proj_b.json()["data"]
        assert proj_b_data["total_courses"] == 0
        b_course_items = [item for item in proj_b_data["items"] if item["source_type"] == "COURSE"]
        assert len(b_course_items) == 0

        # Home B cannot access Home A's course
        b_access = await client.get(f"/api/v1/homes/{home_a_id}/courses", headers=headers_b)
        assert b_access.status_code in (403, 404)

        # -------------------------------------------------------------
        # 9. Verify Zero Database Duplication in events table
        # -------------------------------------------------------------
        async with AsyncSessionLocal() as db_session:
            db_events_count = (await db_session.execute(
                select(func.count(EventModel.id)).where(EventModel.home_id == home_a_id)
            )).scalar()
            # Zero native event records should have been created for courses
            assert db_events_count == 0
