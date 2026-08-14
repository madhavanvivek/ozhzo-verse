# Ozhzo Verse — Phase 4: Tasks & Household Responsibilities Implementation Plan

**Phase**: Phase 4 — Tasks & Household Responsibilities  
**Status**: ARCHITECTURE & PLANNING GATE (No production code written yet)  

---

## 1. Executive Summary
Phase 4 implements the household task coordination engine answering **"WHAT NEEDS TO BE DONE FOR OUR HOME?"**, providing shared household task lists, frictionless quick additions, member assignment, recurring chore schedules, and permanent maintenance history.

---

## 2. Core Domain Entities
1. **`TaskCategory`**: Configurable household categories (`Cleaning`, `Maintenance`, `Bills`, `Vehicle`, `Garden`, `Health`, `Other`).
2. **`TaskTemplate`**: Common household task templates (`Clean Water Filter`, `AC Service`, `Change Bedsheets`, `Car Service`, `Smoke Detector Battery`).
3. **`Task`**: Home-scoped task model (`id`, `home_id`, `category_id`, `template_id`, `title`, `description`, `priority`, `status`, `due_date`, `recurrence_type`, `recurrence_interval_days`, `recurrence_strategy`, `assigned_to`, `created_by`, `completed_by`, `completed_at`, `version`).

---

## 3. Database Schema Changes
- Extend `tasks` table with `category_id`, `template_id`, `priority` (`LOW`, `NORMAL`, `HIGH`, `URGENT`), `status` (`TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`), `recurrence_type`, `recurrence_interval_days`, `recurrence_strategy`, `parent_recurring_task_id`, and `version`.
- Create `task_categories` and `task_templates` tables.
- Add composite index on `(home_id, status, due_date)`.

---

## 4. API Endpoints
- Base: `/api/v1/homes/{home_id}/tasks`
  - `GET /`: List tasks with filters (`view = all | today | upcoming | overdue | my_tasks | completed`, `status`, `assigned_to`, `priority`, `search`, pagination).
  - `POST /`: Quick task creation (`title` required; other fields optional).
  - `GET /{id}`: Fetch task details with assigned member profile.
  - `PATCH /{id}`: Update task details, priority, or due date.
  - `DELETE /{id}`: Cancel/soft-delete task.
  - `POST /{id}/complete`: Complete task and auto-spawn next occurrence if recurring.
  - `POST /{id}/assign`: Assign or unassign task.
  - `GET /summary`: Top KPI summary metrics (Due Today, Overdue, Upcoming, My Tasks).
- Base: `/api/v1/task-templates`
  - `GET /`: List common household task templates.

---

## 5. User Experience (Web & Mobile)
- **Web**: Home Task Board with Overdue, Today, Upcoming, and No Due Date sections; quick add inline bar; common template chips.
- **Mobile**: Fast checklist view with large touch targets, 1-tap completion, and "My Tasks" quick filter.

---

## 6. Recurrence Engine
- Strategy 1: `SCHEDULED_DATE` $\rightarrow \text{next\_due} = \text{current\_due} + \text{interval}$ (e.g. monthly fees).
- Strategy 2: `COMPLETION_DATE` $\rightarrow \text{next\_due} = \text{completed\_at} + \text{interval}$ (e.g. water filter cleaning, car service).
- Concurrency locks prevent duplicate next occurrences.

---

## 7. Security & Tenant Scoping
- All endpoints protected with `require_home_permission(...)`.
- Non-members or cross-home requests receive `403 Forbidden`.
- Server populates `created_by` and `completed_by` from authenticated session.

---

## 8. Testing Strategy
- 17-point automated test suite in `services/api/tests/test_phase4_tasks.py` covering CRUD, assignment, time-window derivations, recurrence engine calculation strategies, completion history, and cross-home isolation.

---

## 9. Quality Gates Sequence (Post-Approval)
1. Apply database schema and model updates.
2. Implement backend schemas and API routers.
3. Update contract generator (`generate_contracts.sh`) for TS and Dart models.
4. Upgrade Web UI (`apps/web`) and Flutter Mobile UI (`apps/mobile`).
5. Execute verification quality gates (`generate_contracts.sh`, `test.sh`, `lint.sh`, `build.sh`).
6. Publish `/docs/PHASE4_IMPLEMENTATION_REPORT.md`.
