# Ozhzo Verse — Phase 5: Bills & Recurring Household Expenses Test Plan

## 1. Scope & Strategy
This test plan validates domestic financial obligations, payment recording, variable utility amounts, partial payments, recurring cycle generation, immutable transaction ledgers, currency handling, and multi-home security isolation.

---

## 2. Test Suite Matrix

### 2.1 Bill CRUD & Responsibility
1. **Quick Bill Creation**: Create bill with title, expected amount (Decimal), and due date. Verify `status = 'UNPAID'`, `amount_paid = 0.00`.
2. **Detailed Bill Creation**: Create recurring bill with category, template reference, responsible member, and recurrence rules (`MONTHLY`, `SCHEDULED_DATE`).
3. **Bill Edit & Optimistic Concurrency**:
   - Update expected amount and due date with matching version.
   - Attempt update with mismatched version $\rightarrow$ returns HTTP 409 Conflict.
4. **Responsible Member Security**:
   - Assign responsible member to active Home A member $\rightarrow$ 200 OK.
   - Attempt assignment to non-member or member of Home B $\rightarrow$ HTTP 400 Bad Request.

### 2.2 Payment Recording & Ledger
5. **Exact Payment**:
   - Expected ₹999, record payment ₹999.
   - Verify `status = 'PAID'`, `amount_paid = 999.00`, payment row created in `bill_payments`.
6. **Variable Utility Payment**:
   - Expected ₹2,000, actual payment ₹2,137.
   - Verify `status = 'PAID'`, `amount_paid = 2137.00`, expected amount preserved at ₹2,000.
7. **Partial Payments**:
   - Expected ₹10,000, initial payment ₹6,000.
   - Verify `status = 'PARTIALLY_PAID'`, remaining balance ₹4,000.
   - Second payment ₹4,000 $\rightarrow$ `status = 'PAID'`, `amount_paid = 10000.00`.
8. **Payment History Ledger Immutability**:
   - Query `/bills/{id}/payments` $\rightarrow$ returns exact sequence of transactions with `paid_by_name`, `payment_method`, and timestamps.

### 2.3 Recurrence & Next Occurrence Spawning
9. **Recurring Bill Completion (`SCHEDULED_DATE`)**:
   - Monthly Internet bill due on 10th.
   - Pay bill on 12th.
   - Verify current bill transitions to `PAID`.
   - Verify next bill occurrence spawned in `UNPAID` state with due date anchored to 10th of next month.
10. **Duplicate Recurrence Prevention**:
    - Concurrent payment requests cannot spawn multiple future occurrences.

### 2.4 Dynamic Time & Status Derivations
11. **Overdue Derivation**: Past due date and status `UNPAID` $\rightarrow$ `is_overdue = True`.
12. **Due Today Derivation**: Today's due date and status `UNPAID` $\rightarrow$ `is_due_today = True`.
13. **Paid Bill Derivation**: Paid bills do not trigger overdue flags.
14. **Summary Metrics**: Verify counts and total amounts for Due Today, Overdue, Upcoming, and Paid This Month.

### 2.5 Security & Multi-Home Isolation
15. **Cross-Home Access Rejection**: User in Home B cannot view or record payments for Home A bills (HTTP 403 Forbidden).
16. **Client ID Tampering Rejection**: Client cannot forge `home_id`, `created_by`, or `paid_by`.
17. **Decimal Precision**: Decimal amounts (e.g. `2137.50`) undergo exact arithmetic without floating point truncation.
