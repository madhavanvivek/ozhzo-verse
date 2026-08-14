# Ozhzo Verse — Phase 5: Bills & Recurring Household Expenses Requirements

## 1. Functional Requirements

### 1.1 Home-Scoped Bill Management
- **FR-BILL-01**: Every Home maintains a unified ledger of recurring and upcoming household bills.
- **FR-BILL-02**: Quick creation requires `title`, `amount` (expected amount), and `due_date`.
- **FR-BILL-03**: Optional bill attributes: `category_id`, `template_id`, `currency` (defaults to home currency), `recurrence_type` (`NONE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `YEARLY`, `CUSTOM_DAYS`), `recurrence_interval_days`, `recurrence_strategy` (`SCHEDULED_DATE`, `PAYMENT_DATE`), `responsible_member_id`, `notes`.

### 1.2 Payment Recording & Financial Ledger
- **FR-PAY-01**: Recording a payment captures: `amount_paid` (Decimal $> 0$), `paid_date` (Date), `paid_by` (authenticated user or selected active member), `payment_method` (`CASH`, `BANK_TRANSFER`, `UPI`, `CARD`, `ONLINE`, `OTHER`), `receipt_url`, `notes`.
- **FR-PAY-02**: The system supports **Partial Payments**:
  - If $\sum \text{payments} < \text{expected\_amount}$, bill status becomes `PARTIALLY_PAID`.
  - If $\sum \text{payments} \ge \text{expected\_amount}$, bill status becomes `PAID`.
- **FR-PAY-03**: Variable actual amounts are supported without overwriting the expected amount.

### 1.3 Recurrence & Next Bill Occurrence Spawning
- **FR-REC-01**: When a recurring bill is fully `PAID`, the system atomically spawns the next occurrence in `UNPAID` state.
- **FR-REC-02**: Recurrence strategies:
  - `SCHEDULED_DATE`: Next due date computed from scheduled `due_date` (e.g. 10th of next month).
  - `PAYMENT_DATE`: Next due date computed from `paid_date` $+ \text{interval}$.
- **FR-REC-03**: Concurrency lock prevents duplicate next-occurrence creation.

### 1.4 Dynamic Status & Time Derivations
- **FR-TIME-01**: Persistent states: `UNPAID`, `PARTIALLY_PAID`, `PAID`, `CANCELLED`.
- **FR-TIME-02**: Derived time states:
  - `OVERDUE`: $\text{due\_date} < \text{today} \land \text{status} \in (\text{'UNPAID'}, \text{'PARTIALLY\_PAID'})$.
  - `DUE_TODAY`: $\text{due\_date} == \text{today} \land \text{status} \neq \text{'PAID'}$.
  - `UPCOMING`: $\text{due\_date} > \text{today} \land \text{status} \neq \text{'PAID'}$.

### 1.5 Bill Categories & Templates
- **FR-CAT-01**: Dynamic Home categories (`Utilities`, `Housing`, `Education`, `Insurance`, `Transportation`, `Subscriptions`, `Loans`, `Maintenance`, `Other`).
- **FR-TPL-01**: Global templates catalog for common household bills (`Electricity`, `Water`, `Piped Gas`, `Fiber Internet`, `House Rent`, `Car Insurance`, `Property Tax`).

---

## 2. Non-Functional Requirements

### 2.1 Security & Multi-Home Isolation
- **NFR-SEC-01**: Every endpoint validates `require_home_permission(...)`.
  - `bills:view`: All active members.
  - `bills:create`, `bills:edit`: `HOME_ADMIN`, `MEMBER`.
  - `bills:pay`: `HOME_ADMIN`, `MEMBER`.
  - `bills:delete`: `HOME_ADMIN`.
- **NFR-SEC-02**: Cross-home access rejected with `403 Forbidden`.
- **NFR-SEC-03**: Assigning responsible member or recording payer validates target user is an `ACTIVE` member of the same Home.

### 2.2 Financial Precision & Data Integrity
- **NFR-FIN-01**: Monetary fields stored as `NUMERIC(12, 2)` and manipulated with Python `Decimal`.
- **NFR-FIN-02**: Payment records in `bill_payments` are immutable append-only ledger entries.
- **NFR-FIN-03**: Optimistic concurrency via `version` column prevents race conditions.
