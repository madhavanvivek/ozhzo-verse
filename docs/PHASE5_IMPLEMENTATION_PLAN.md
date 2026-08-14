# Ozhzo Verse — Phase 5: Bills & Recurring Household Expenses Implementation Plan

**Phase**: Phase 5 — Bills & Recurring Household Expenses  
**Status**: ARCHITECTURE & PLANNING GATE (No production code written yet)  

---

## 1. Executive Summary
Phase 5 establishes the household domestic financial obligation ledger answering **"WHAT DO WE HAVE TO PAY FOR OUR HOME, HOW MUCH, WHEN, WHO IS RESPONSIBLE, AND WAS IT PAID?"**, providing shared bill tracking, variable utility amount recording, partial payments, recurring payment rhythms, and permanent financial history.

---

## 2. Core Domain Entities
1. **`BillCategory`**: Dynamic household categories (`Utilities`, `Housing`, `Education`, `Insurance`, `Transportation`, `Subscriptions`, `Loans`, `Taxes`, `Maintenance`, `Other`).
2. **`BillTemplate`**: Ready-to-use common household bills catalog (`Electricity`, `Water`, `Piped Gas`, `Fiber Internet`, `House Rent`, `Car Insurance`, `Property Tax`).
3. **`Bill`**: Obligation entity (`id`, `home_id`, `category_id`, `template_id`, `title`, `expected_amount`, `currency`, `due_date`, `recurrence_type`, `recurrence_interval_days`, `recurrence_strategy`, `status`, `amount_paid`, `responsible_member_id`, `version`, `created_by`).
4. **`BillPayment`**: Immutable payment ledger entity (`id`, `home_id`, `bill_id`, `amount_paid`, `currency`, `paid_date`, `paid_by`, `payment_method`, `receipt_url`, `notes`, `created_at`).

---

## 3. Database Layer Additions (Post-Approval)
- Create `bill_categories` and `bill_templates` tables.
- Upgrade `bills` table with `expected_amount`, `amount_paid`, `status` (`UNPAID`, `PARTIALLY_PAID`, `PAID`, `CANCELLED`), `recurrence_type`, `recurrence_interval_days`, `recurrence_strategy`, `parent_recurring_bill_id`, `responsible_member_id`, and `version`.
- Upgrade `bill_payments` table with `home_id`, `currency`, `payment_method` (`CASH`, `BANK_TRANSFER`, `UPI`, `CARD`, `ONLINE`, `OTHER`), `receipt_url`, `notes`.
- Add compound indexes for fast query performance.

---

## 4. API Endpoints Specification
- Base: `/api/v1/homes/{home_id}/bills`
  - `GET /`: List bills with view filters (`all`, `due_today`, `overdue`, `upcoming`, `paid`, `my_responsible`), search, and pagination.
  - `POST /`: Quick Add bill (`title`, `expected_amount`, `due_date` required).
  - `GET /{id}`: Fetch single bill with payment history and remaining balance.
  - `PATCH /{id}`: Partial update with optimistic locking (`version`).
  - `DELETE /{id}`: Soft-delete / cancel bill.
  - `POST /{id}/payments`: Record full or partial payment, update balance/status, and auto-spawn next occurrence if recurring.
  - `GET /{id}/payments`: Fetch payment ledger for bill.
  - `GET /summary`: Financial KPI metrics (Due Today count/amount, Overdue count/amount, Upcoming count/amount, Paid This Month count/amount).
  - `GET/POST /categories`: Home bill categories management.
- Base: `/api/v1/bill-templates`
  - `GET /`: List global common household bill templates.

---

## 5. UI/UX Workflows (Web & Mobile)
- **Web**: Bills Dashboard with Top Financial Metrics, Inline Quick Add Bar, Common Routine preset chips, sectioned list (Overdue, Due Today, Upcoming, Paid), and Payment Logging modal.
- **Mobile**: Touch-optimized checklist with prominent due dates, amounts, and 1-tap `[ Mark as Paid ]` action.

---

## 6. Testing Strategy
- Comprehensive test suite in `services/api/tests/test_phase5_bills.py` covering:
  1. Quick bill creation.
  2. Detailed recurring bill creation.
  3. Exact payment recording.
  4. Variable utility payment recording (expected vs actual preservation).
  5. Partial payments and balance calculations.
  6. Recurring bill completion with `SCHEDULED_DATE` vs `PAYMENT_DATE`.
  7. Duplicate next-occurrence prevention.
  8. Time derivations (`OVERDUE`, `DUE_TODAY`, `UPCOMING`).
  9. Payment history ledger immutability.
  10. Multi-home isolation and cross-home assignment rejection.
  11. Decimal monetary precision.

---

## 7. Quality Gates Sequence (Post-Approval)
1. Apply database schema changes and ORM models.
2. Implement backend schemas and API routers.
3. Update contract generator (`generate_contracts.sh`) for TS and Dart models.
4. Upgrade Web UI (`apps/web`) and Flutter Mobile UI (`apps/mobile`).
5. Execute verification quality gates (`generate_contracts.sh`, `test.sh`, `lint.sh`, `build.sh`).
6. Publish `/docs/PHASE5_IMPLEMENTATION_REPORT.md`.
