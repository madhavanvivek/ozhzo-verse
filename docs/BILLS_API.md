# Ozhzo Verse — Phase 5: Bills & Recurring Household Expenses API Specification

## 1. Base URL & Security Headers
All endpoints are Home-scoped:
```
BASE_URL: /api/v1/homes/{home_id}/bills
Headers:
  Authorization: Bearer <access_token>
```
Every endpoint enforces `require_home_permission(...)`.

---

## 2. API Endpoints Specification

### 2.1 Bill CRUD Endpoints

#### `GET /api/v1/homes/{home_id}/bills`
- **Permission**: `bills:view`
- **Query Params**:
  - `view`: string (options: `all`, `due_today`, `overdue`, `upcoming`, `paid`, `my_responsible`)
  - `status`: string (`UNPAID`, `PARTIALLY_PAID`, `PAID`, `CANCELLED`, `ALL`)
  - `category_id`: UUID
  - `responsible_member_id`: UUID
  - `search`: string
  - `sort_by`: string (`due_date`, `expected_amount`, `title`, `created_at`)
  - `order`: `asc` | `desc`
  - `page`: int (default 1), `page_size`: int (default 20, max 100)
- **Response**: Paginated list of bills with derived time flags (`is_overdue`, `is_due_today`), remaining balance (`remaining_balance = expected_amount - amount_paid`), and member display names.

#### `POST /api/v1/homes/{home_id}/bills`
- **Permission**: `bills:create`
- **Request Body**:
  ```json
  {
    "title": "Electricity Bill (BESCOM)",
    "expected_amount": "2000.00",
    "currency": "INR",
    "due_date": "2026-08-20",
    "recurrence_type": "MONTHLY",
    "recurrence_strategy": "SCHEDULED_DATE",
    "category_id": "uuid (optional)",
    "template_id": "uuid (optional)",
    "responsible_member_id": "uuid (optional)",
    "notes": "Meter RR No: 4421-E"
  }
  ```

#### `GET /api/v1/homes/{home_id}/bills/{bill_id}`
- **Permission**: `bills:view`
- **Response**: Full bill details including complete payments ledger history and remaining balance.

#### `PATCH /api/v1/homes/{home_id}/bills/{bill_id}`
- **Permission**: `bills:edit`
- **Request Body**: Partial update (`title`, `expected_amount`, `due_date`, `recurrence_type`, `responsible_member_id`, `category_id`, `notes`, `version`).

#### `DELETE /api/v1/homes/{home_id}/bills/{bill_id}`
- **Permission**: `bills:delete`
- **Behavior**: Soft-deletes bill and marks `status = 'CANCELLED'`.

---

### 2.2 Payment Recording Endpoints

#### `POST /api/v1/homes/{home_id}/bills/{bill_id}/payments`
- **Permission**: `bills:pay`
- **Request Body**:
  ```json
  {
    "amount_paid": "2137.00",
    "currency": "INR",
    "paid_date": "2026-08-12",
    "paid_by": "uuid (optional, defaults to current user)",
    "payment_method": "UPI",
    "receipt_url": "https://... (optional)",
    "notes": "Paid via GooglePay Txn #994821",
    "version": 1
  }
  ```
- **Behavior**:
  1. Validates optimistic concurrency version on `bills`.
  2. Inserts immutable record in `bill_payments`.
  3. Increments `bills.amount_paid += payload.amount_paid`.
  4. If `bills.amount_paid >= bills.expected_amount`:
     - Updates `bills.status = 'PAID'`.
     - If bill has recurrence (`recurrence_type != 'NONE'`), atomically spawns next occurrence in `UNPAID` state with `amount_paid = 0.00`.
  5. Else (`bills.amount_paid < bills.expected_amount`):
     - Updates `bills.status = 'PARTIALLY_PAID'`.
- **Response**: Updated bill DTO with appended payment entry.

#### `GET /api/v1/homes/{home_id}/bills/{bill_id}/payments`
- **Permission**: `bills:view`
- **Response**: Chronological list of payments made against this bill.

---

### 2.3 Bill Templates Catalog & KPI Summary

#### `GET /api/v1/bill-templates`
- **Permission**: Authenticated
- **Response**: List of pre-configured global bill templates (Electricity, Water, Internet, Rent, Insurance, etc.).

#### `GET /api/v1/homes/{home_id}/bills/summary`
- **Permission**: `bills:view`
- **Response**:
  ```json
  {
    "total_unpaid_count": 5,
    "total_unpaid_amount": "14500.00",
    "due_today_count": 2,
    "due_today_amount": "3136.00",
    "overdue_count": 1,
    "overdue_amount": "2000.00",
    "upcoming_count": 2,
    "upcoming_amount": "9364.00",
    "paid_this_month_count": 6,
    "paid_this_month_amount": "28450.00",
    "currency": "INR"
  }
  ```
