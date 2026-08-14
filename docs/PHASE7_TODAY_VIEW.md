# Ozhzo Verse — Phase 7: Unified Today View Specification

## 1. Objective & Product Principle
The **Unified Today View** provides a single, chronological agenda combining all domestic responsibilities, schedules, and alerts for the current calendar date without duplicating records in the database.

---

## 2. Source Domains & Mapping

| Domain Source | Selection Criteria | Projection Mapping | Navigation Target |
|---|---|---|---|
| **Events (`events`)** | `start_time <= end_of_today AND end_time >= start_of_today AND deleted_at IS NULL` | `source_type: 'EVENT'`, `title: e.title`, `time: e.start_time`, `all_day: e.is_all_day` | `/calendar/{id}` |
| **Tasks (`tasks`)** | `due_date = today_date AND status != 'COMPLETED' AND deleted_at IS NULL` | `source_type: 'TASK'`, `title: t.title`, `time: 18:00 UTC`, `priority: t.priority` | `/tasks/{id}` |
| **Bills (`bills`)** | `due_date = today_date AND status IN ('UNPAID', 'PARTIALLY_PAID') AND deleted_at IS NULL` | `source_type: 'BILL'`, `title: b.title`, `time: 23:59 UTC`, `meta: {amount, currency}` | `/bills/{id}` |
| **Purchase Items (`purchase_items`)** | `is_checked = FALSE AND priority IN ('URGENT', 'HIGH')` | `source_type: 'PURCHASE'`, `title: p.name`, `meta: {quantity, unit}` | `/purchase-list` |
| **Low Stock Supplies (`inventory_items`)** | `item_type = 'CONSUMABLE' AND status = 'OUT_OF_STOCK' AND deleted_at IS NULL` | `source_type: 'INVENTORY'`, `title: i.name`, `meta: {quantity, min_threshold}` | `/inventory/{id}` |
| **Asset Loans (`asset_loans`)** | `status = 'ACTIVE' AND expected_return_date <= today_date` | `source_type: 'ASSET'`, `title: a.name`, `meta: {borrower, return_date}` | `/inventory/assets/{id}` |

---

## 3. Today Endpoint Specification

### `GET /api/v1/homes/{home_id}/today`
- **Auth**: Bearer Token (`homes:view`)
- **Query Params**:
  - `timezone`: Optional string (defaults to `homes.timezone` or `UTC`).
  - `include_all`: boolean (default `true`).
- **Response Structure**:
  ```json
  {
    "date": "2026-08-15",
    "timezone": "Asia/Kolkata",
    "summary": {
      "total_items": 6,
      "events_count": 2,
      "tasks_count": 1,
      "bills_count": 1,
      "purchase_urgent_count": 1,
      "inventory_alerts_count": 1
    },
    "timeline": [
      {
        "source_type": "EVENT",
        "source_id": "uuid-evt-1",
        "title": "Grandmother's 80th Birthday",
        "start": "2026-08-15T00:00:00Z",
        "end": "2026-08-15T23:59:59Z",
        "all_day": true,
        "priority": "NORMAL",
        "status": "CONFIRMED",
        "navigation_target": "/calendar/uuid-evt-1"
      },
      {
        "source_type": "EVENT",
        "source_id": "uuid-evt-2",
        "title": "Doctor Appointment — City Clinic",
        "start": "2026-08-15T10:30:00Z",
        "end": "2026-08-15T11:30:00Z",
        "all_day": false,
        "priority": "HIGH",
        "status": "CONFIRMED",
        "navigation_target": "/calendar/uuid-evt-2"
      },
      {
        "source_type": "TASK",
        "source_id": "uuid-task-1",
        "title": "Clean Water Filter",
        "start": "2026-08-15T18:00:00Z",
        "end": "2026-08-15T18:00:00Z",
        "all_day": false,
        "priority": "NORMAL",
        "status": "TODO",
        "navigation_target": "/tasks/uuid-task-1"
      },
      {
        "source_type": "BILL",
        "source_id": "uuid-bill-1",
        "title": "BESCOM Electricity Bill",
        "start": "2026-08-15T23:59:59Z",
        "end": "2026-08-15T23:59:59Z",
        "all_day": true,
        "priority": "HIGH",
        "status": "UNPAID",
        "navigation_target": "/bills/uuid-bill-1"
      }
    ],
    "attention_alerts": [
      {
        "source_type": "INVENTORY",
        "source_id": "uuid-inv-1",
        "title": "Basmati Rice (Out of Stock)",
        "priority": "HIGH",
        "navigation_target": "/inventory/uuid-inv-1"
      },
      {
        "source_type": "PURCHASE",
        "source_id": "uuid-pur-1",
        "title": "Milk (2 L) — Urgent Purchase",
        "priority": "HIGH",
        "navigation_target": "/purchase-list"
      }
    ]
  }
  ```
