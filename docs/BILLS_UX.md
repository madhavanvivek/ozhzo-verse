# Ozhzo Verse — Phase 5: Bills & Recurring Household Expenses UI/UX Design

## 1. UX Design Philosophy
- **Clarity of Household Outflows**: Answer in 3 seconds: *"What bills are due, how much, and who is taking care of them?"*
- **Frictionless Payment Logging**: Recording a payment requires only entering the amount paid and tapping Save.
- **Zero Banking Gimmicks**: Ozhzo is a household ledger, not a bank or checkout gateway. We report and coordinate payments made by the household.

---

## 2. Key Screen Layouts & User Journeys

### 2.1 Web Bills Dashboard
- **Top Financial Summary Cards**:
  - `Due Today` (e.g. 🔴 2 Bills • ₹3,136)
  - `Overdue` (e.g. ⚠️ 1 Bill • ₹2,000)
  - `Upcoming` (e.g. 🟢 2 Bills • ₹9,364)
  - `Paid This Month` (e.g. 💳 6 Bills • ₹28,450)
- **Inline Quick Add Bar**:
  - `[ Bill Title... ] [ Expected Amount ] [ Due Date ▾ ] [ Responsible Member ▾ ] [ + Add Bill ]`
- **Common Bill Template Preset Chips**:
  - `+ Electricity`, `+ Water`, `+ Internet`, `+ House Rent`, `+ Gas Cylinder`, `+ Car Insurance`
- **Sectioned Bills List**:
  - **OVERDUE** (Urgent visual cue)
    - `Electricity Bill — Expected ₹2,000 • Overdue by 2 days • Responsible: Vivek • [ Record Payment ]`
  - **DUE TODAY**
    - `Fiber Internet — Expected ₹999 • Due Today • Responsible: Karthika • [ Record Payment ]`
  - **UPCOMING**
    - `House Rent — Expected ₹25,000 • Due 1st of month • Responsible: Vivek`
  - **PAID THIS MONTH**
    - `Piped Gas — Paid ₹842 on 8 Aug by Karthika (UPI)`

### 2.2 Payment Modal Dialog
- `Amount Paid`: Pre-filled with expected amount, fully editable for variable utility bills.
- `Paid Date`: Defaults to today.
- `Paid By`: Defaults to current user, dropdown allows selecting another active member.
- `Payment Method`: `UPI` | `Card` | `Bank Transfer` | `Cash` | `Other`.
- `Notes / Transaction Ref`: Optional reference string.
- Action: `[ Save Payment ]`.

### 2.3 Mobile Experience (Flutter)
- Large touch cards showing Bill Name, Due Date, Expected Amount, and prominent `[ Mark as Paid ]` button.
- Fast swipe-to-pay confirmation.

---

## 3. User Journeys

```
Journey 1: Quick Bill Setup
Vivek sets up the new home ➔ Clicks "+ Internet" template ➔ Sets expected ₹999, Due 10th of every month ➔ Assigns Karthika as responsible ➔ Bill is scheduled.

Journey 2: Variable Electricity Bill Payment
Electricity bill arrives for ₹2,137 (expected was ₹2,000) ➔ Vivek opens Ozhzo ➔ Taps "Record Payment" on Electricity ➔ Inputs ₹2,137 ➔ Selects UPI ➔ Taps Save ➔ Status becomes PAID, payment recorded in history, next month's bill scheduled automatically.

Journey 3: Split / Partial School Fee Payment
School fee is ₹10,000 ➔ Karthika pays ₹6,000 today ➔ Records ₹6,000 payment ➔ Bill updates to PARTIALLY_PAID (Balance: ₹4,000) ➔ Vivek pays remaining ₹4,000 next week ➔ Bill transitions to PAID.
```
