# Ozhzo Verse — Phase 4: Tasks & Household Responsibilities API Specification

## 1. Base URL & Security Headers
All endpoints are Home-scoped:
```
BASE_URL: /api/v1/homes/{home_id}/tasks
Headers:
  Authorization: Bearer <access_token>
```
Every endpoint validates `require_home_permission(...)`.

---

## 2. API Endpoints Specification

### 2.1 Task CRUD Endpoints

#### `GET /api/v1/homes/{home_id}/tasks`
- **Permission**: `tasks:view`
- **Query Params**:
  - `status`: string (default `TODO`, options: `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `ALL`)
  - `view`: string (options: `all`, `today`, `upcoming`, `overdue`, `my_tasks`, `completed`)
  - `assigned_to`: UUID (filter by specific member)
  - `priority`: string (`LOW`, `NORMAL`, `HIGH`, `URGENT`)
  - `search`: string (case-insensitive search on title/description)
  - `sort_by`: string (`due_date`, `priority`, `created_at`, `title`)
  - `order`: `asc` | `desc`
  - `page`: int (default 1), `page_size`: int (default 20, max 100)
- **Response**: Paginated list of tasks with derived time flags (`is_overdue`, `is_due_today`) and member display names.

#### `POST /api/v1/homes/{home_id}/tasks`
- **Permission**: `tasks:create`
- **Request Body**:
  ```json
  {
    "title": "Clean water filter",
    "description": "Replace sediment pre-filter candle and sanitize bowl",
    "priority": "NORMAL",
    "assigned_to": "uuid (optional)",
    "due_date": "2026-08-20T18:00:00Z (optional)",
    "recurrence_type": "CUSTOM_DAYS",
    "recurrence_interval_days": 30,
    "recurrence_strategy": "COMPLETION_DATE",
    "category_id": "uuid (optional)",
    "template_id": "uuid (optional)"
  }
  ```

#### `GET /api/v1/homes/{home_id}/tasks/{task_id}`
- **Permission**: `tasks:view`
- **Response**: Full task details with assigned member, creator profile, and recurrence metadata.

#### `PATCH /api/v1/homes/{home_id}/tasks/{task_id}`
- **Permission**: `tasks:edit`
- **Request Body**: Partial update (`title`, `description`, `priority`, `status`, `assigned_to`, `due_date`, `recurrence_type`, `version`).

#### `DELETE /api/v1/homes/{home_id}/tasks/{task_id}`
- **Permission**: `tasks:delete`
- **Behavior**: Soft-deletes task and sets `status = 'CANCELLED'`.

---

### 2.2 Task Lifecycle Actions

#### `POST /api/v1/homes/{home_id}/tasks/{task_id}/complete`
- **Permission**: `tasks:complete`
- **Request Body**:
  ```json
  {
    "notes": "Replaced with 5 micron sediment candle",
    "version": 1
  }
  ```
- **Behavior**:
  1. Validates optimistic concurrency version.
  2. Sets `status = 'COMPLETED'`, `completed_by = current_user.id`, `completed_at = NOW()`.
  3. If task has recurrence (`recurrence_type != 'NONE'`), automatically computes next `due_date` and generates the next occurrence in `TODO` state.
- **Response**: Updated completed task DTO with reference to next generated task ID (if applicable).

#### `POST /api/v1/homes/{home_id}/tasks/{task_id}/assign`
- **Permission**: `tasks:edit`
- **Request Body**: `{ "assigned_to": "uuid" }` (or `null` to unassign).

---

### 2.3 Task Templates Catalog & Summary

#### `GET /api/v1/task-templates`
- **Permission**: Authenticated
- **Response**: List of pre-configured common household task templates (AC service, water filter, car maintenance, deep cleaning).

#### `GET /api/v1/homes/{home_id}/tasks/summary`
- **Permission**: `tasks:view`
- **Response**:
  ```json
  {
    "total_active": 14,
    "due_today": 3,
    "overdue": 2,
    "upcoming": 9,
    "my_tasks": 4,
    "completed_history_count": 82
  }
  ```
