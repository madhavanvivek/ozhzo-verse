# Ozhzo Verse — Phase 5 Architecture Review: Bills & Recurring Household Expenses

This document provides explicit architectural answers for the Phase 5 Planning Gate.

---

## 1. What is a Bill?
In Ozhzo Verse, a **Bill** represents a recurring or one-time domestic financial obligation that the household is expected to pay.
- Examples: *Electricity Bill*, *Water Bill*, *Internet Subscription*, *House Rent*, *School Tuition Fee*, *Property Tax*, *Car Insurance*.
- It defines the expected amount, due date, category, recurrence rules, and responsible member.

---

## 2. What is an Expense / Payment?
A **Payment / Expense** represents an executed financial settlement transaction logged by a household member against a bill.
- Examples: *Paid ₹2,137 on 12 Aug via UPI by Vivek*.
- It captures the actual amount transferred, payment date, payer, payment method, and optional receipt.

---

## 3. How are they related?
- One **Bill** has many **Payments** ($1 \rightarrow N$).
- The `bills` table manages the obligation lifecycle, expected amount, and active cycle state.
- The `bill_payments` table is an immutable transaction ledger recording each payment event.
- $\text{Remaining Balance} = \text{bills.expected\_amount} - \text{bills.amount\_paid}$.

---

## 4. How are recurring bills generated?
- When a bill is marked fully `PAID` (or when payments reach/exceed the expected amount), the system evaluates its recurrence definition.
- The recurrence engine calculates the next `due_date` and atomically creates the next cycle instance in `UNPAID` state with `amount_paid = 0.00` and a reference to `parent_recurring_bill_id`.

---

## 5. How are variable amounts handled?
- Variable utility bills (Electricity, Water, Piped Gas) define an **`expected_amount`** (e.g. ₹2,000).
- When the invoice arrives, the member logs the actual invoice payment in `bill_payments` (e.g. ₹2,137).
- Both values are stored and preserved: the expected baseline in `bills.expected_amount` and the actual payment in `bill_payments.amount_paid`.

---

## 6. How are expected vs actual amounts preserved?
- `bills.expected_amount`: Retains the configured or estimated obligation amount.
- `bills.amount_paid`: Aggregates the sum of actual payments made during the cycle.
- `bill_payments.amount_paid`: Preserves the exact amount of each individual transaction.
- The system never silently overwrites the expected baseline with the actual payment.

---

## 7. How are partial payments handled?
- A bill of ₹10,000 can receive multiple partial payments:
  1. Payment 1: ₹6,000 $\rightarrow$ `bills.amount_paid = 6000.00`, `bills.status = 'PARTIALLY_PAID'`, Balance: ₹4,000.
  2. Payment 2: ₹4,000 $\rightarrow$ `bills.amount_paid = 10000.00`, `bills.status = 'PAID'`, Balance: ₹0.00.
- When `amount_paid >= expected_amount`, the bill transitions to `PAID` and triggers next-occurrence generation if recurring.

---

## 8. How is payment history preserved?
- Every payment is recorded as an immutable row in `bill_payments`.
- Historical payment entries are never deleted or modified when a recurring cycle advances; they remain permanently queryable for annual expense tracking and maintenance verification.

---

## 9. Who is responsible vs who paid?
- **`responsible_member_id`**: The family member responsible for monitoring, verifying, and coordinating the bill.
- **`paid_by`**: The family member who physically paid the funds.
- These fields are completely separate and both are home-scoped.

---

## 10. How are overdue states derived?
- Overdue is a **dynamically derived calculation**, not a static database status string:
  $$\text{is\_overdue} = (\text{due\_date} < \text{today}) \land (\text{status} \in [\text{'UNPAID'}, \text{'PARTIALLY\_PAID'}])$$
- Guaranteed real-time accuracy without background cron status mutations.

---

## 11. How is currency handled?
- Currency is anchored to the Home's default currency (`homes.currency`, e.g. `INR`, `AED`, `USD`, `EUR`, `GBP`).
- Individual bills store their currency code explicitly (`bills.currency`), defaulting to the Home currency.
- All monetary arithmetic is performed using Python `Decimal` and PostgreSQL `NUMERIC(12, 2)`.

---

## 12. How is multi-home isolation enforced?
- Every query and mutation enforces `home_id = home_ctx.home_id`.
- Users in Home B cannot view or pay bills in Home A (HTTP 403 Forbidden).
- Compound database indexes prefix `(home_id, ...)`.

---

## 13. How is RBAC enforced?
- Reuses existing Ozhzo Home RBAC:
  - `bills:view`: All active home members (`OWNER`, `ADMIN`, `MEMBER`, `CHILD`, `GUEST`).
  - `bills:create`, `bills:edit`: `OWNER`, `ADMIN`, `MEMBER`.
  - `bills:pay`: `OWNER`, `ADMIN`, `MEMBER`.
  - `bills:delete`: `OWNER`, `ADMIN`.

---

## 14. How are concurrent payments prevented?
- Optimistic concurrency locking via integer `version` on `bills`.
- If two family members record payments simultaneously, the second transaction detects the version increment and is safely reconciled or retried.

---

## 15. How are duplicate recurring bills prevented?
- Marking a bill `PAID` and spawning the next cycle occurrence execute within a single atomic database transaction.
- Concurrency locks on the bill record prevent multiple concurrent requests from spawning duplicate future occurrences.

---

## 16. How does Phase 5 reuse Phase 4 recurrence architecture?
- Reuses the unified recurrence models:
  - `recurrence_type`: `NONE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `YEARLY`, `CUSTOM_DAYS`.
  - `recurrence_strategy`:
    - `SCHEDULED_DATE`: Anchored to calendar due dates (e.g. 1st or 10th of next month).
    - `PAYMENT_DATE`: Anchored to actual payment date $+ \text{interval}$.

---

## 17. How can Bills later connect to Tasks?
- Prepared future relationship: A bill can have an associated task (e.g. *Bill: "Internet Bill"* $\rightarrow$ *Task: "Pay Internet Bill"*).
- Kept decoupled in Phase 5 to avoid artificial complexity.

---

## 18. How can Bills later connect to Assets?
- Prepared future relationship: A bill can reference `asset_id` (e.g. *Car Insurance Bill* $\rightarrow$ *Asset: Family SUV*).

---

## 19. How can Bills later connect to Inventory?
- Prepared future relationship: Recurring pantry restock budgets or subscription supplies.

---

## 20. What is explicitly OUT OF SCOPE?
- **Payment Gateway Processing**: Ozhzo does not process bank transactions or integrate Stripe/Razorpay checkouts for utility bills. It is a domestic tracking and coordination ledger.
- **Invoicing & Commercial Accounting**: No double-entry accounting books, general ledgers, accounts payable aging schedules, or tax filing.
- **Automated Bank Sync / Open Banking**: No screen scraping or Plaid/Yodlee bank feed integrations in Phase 5.
