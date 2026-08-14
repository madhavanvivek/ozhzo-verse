# Ozhzo Verse — Phase 6: Shared Calendar & Household Events API Specification

## 1. Base URL & Security Headers
All endpoints are Home-scoped:
```
BASE_URL: /api/v1/homes/{home_id}/events
Headers:
  Authorization: Bearer <access_token>
```
Every endpoint enforces `require_home_permission(...)`.

---

## 2. API Endpoints Specification

### 2.1 Event CRUD Endpoints

#### `GET /api/v1/homes/{home_id}/events`
- **Permission**: `calendar:view`
- **Query Params**:
  - `start_date`: ISO datetime (e.g. `2026-08-01T00:00:00Z`)
  - `end_date`: ISO datetime (e.g. `2026-08-31T23:59:59Z`)
  - `category_id`: UUID
  - `status`: `CONFIRMED` | `TENTATIVE` | `CANCELLED`
  - `participant_id`: UUID
  - `search`: string
- **Response**: List of `EventDTO` with populated participants and category metadata.

#### `POST /api/v1/homes/{home_id}/events`
- **Permission**: `calendar:create`
- **Request Body**:
  ```json
  {
    "title": "Parent-Teacher Meeting",
    "description": "Discuss Math and Science progress",
    "location": "Oakridge School Room 204",
    "start_time": "2026-08-18T10:00:00Z",
    "end_time": "2026-08-18T11:00:00Z",
    "is_all_day": false,
    "category_id": "uuid (optional)",
    "reminder_minutes_before": 60,
    "recurrence_type": "NONE",
    "participant_user_ids": ["uuid_karthika", "uuid_vivek"]
  }
  ```
- **Response (201 Created)**: Created `EventDTO`.

#### `GET /api/v1/homes/{home_id}/events/{event_id}`
- **Permission**: `calendar:view`
- **Response**: Single `EventDTO` with participant response statuses.

#### `PATCH /api/v1/homes/{home_id}/events/{event_id}`
- **Permission**: `calendar:edit`
- **Request Body**: Partial update with optimistic locking (`version`).

#### `DELETE /api/v1/homes/{home_id}/events/{event_id}`
- **Permission**: `calendar:delete`
- **Behavior**: Soft-deletes event and marks `status = 'CANCELLED'`.

#### `POST /api/v1/homes/{home_id}/events/{event_id}/participants/{user_id}/status`
- **Permission**: `calendar:view` (User updating own status)
- **Request Body**: `{"status": "ACCEPTED" | "DECLINED"}`

---

### 2.2 Unified Calendar Projection Endpoint

#### `GET /api/v1/homes/{home_id}/calendar/projection`
- **Permission**: `calendar:view`
- **Query Params**:
  - `start_date`: ISO datetime (Required)
  - `end_date`: ISO datetime (Required)
  - `include_tasks`: boolean (default `true`)
  - `include_bills`: boolean (default `true`)
- **Response**:
  ```json
  {
    "start_date": "2026-08-15T00:00:00Z",
    "end_date": "2026-08-22T23:59:59Z",
    "items": [
      {
        "id": "uuid-evt-1",
        "item_type": "EVENT",
        "title": "Grandmother's 80th Birthday",
        "start_time": "2026-08-15T00:00:00Z",
        "end_time": "2026-08-15T23:59:59Z",
        "is_all_day": true,
        "location": "Family Home",
        "category_name": "Birthday",
        "status": "CONFIRMED"
      },
      {
        "id": "uuid-task-2",
        "item_type": "TASK",
        "title": "Clean Water Filter",
        "start_time": "2026-08-16T18:00:00Z",
        "end_time": "2026-08-16T18:00:00Z",
        "is_all_day": false,
        "category_name": "Maintenance",
        "status": "TODO",
        "assigned_to_name": "Vivek"
      },
      {
        "id": "uuid-bill-3",
        "item_type": "BILL",
        "title": "BESCOM Electricity Bill Due",
        "start_time": "2026-08-20T23:59:59Z",
        "end_time": "2026-08-20T23:59:59Z",
        "is_all_day": true,
        "category_name": "Utilities",
        "status": "UNPAID",
        "expected_amount": "2000.00",
        "currency": "INR"
      }
    ]
  }
  ```
