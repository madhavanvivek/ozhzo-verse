# Ozhzo Verse — Phase 7: Attention Center & Real-Time Pulse

## 1. Objective & Philosophy
The **Attention Center** aggregates high-signal, actionable items across the home. Rather than overwhelming users with noisy push notifications, it provides a quiet, ranked digest of items requiring attention.

---

## 2. Priority Hierarchy & Derivation Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ATTENTION SEVERITY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔴 CRITICAL (Action Required Urgently)                                      │
│    • Overdue Bills (due_date < today AND status IN ('UNPAID', 'PARTIALLY')) │
│    • Overdue Tasks (due_date < today AND status != 'COMPLETED')            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟠 HIGH (Due / Needed Today)                                                │
│    • Bills Due Today                                                        │
│    • Tasks Due Today                                                        │
│    • Consumables Out of Stock (quantity = 0)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟡 NORMAL (Upcoming / Low Stock)                                            │
│    • Low Stock Consumables (0 < quantity <= min_threshold)                 │
│    • Overdue Asset Return (asset_loans.expected_return_date < today)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔵 INFO (Awareness Only)                                                    │
│    • Events Happening Today                                                 │
│    • Pending Home Invitations (status = 'PENDING')                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Attention Endpoint Specification

### `GET /api/v1/homes/{home_id}/attention`
- **Auth**: Bearer Token (`homes:view`)
- **Response Structure**:
  ```json
  {
    "summary": {
      "critical_count": 1,
      "high_count": 2,
      "normal_count": 1,
      "info_count": 1,
      "total_attention_items": 5
    },
    "items": [
      {
        "id": "uuid-bill-1",
        "severity": "CRITICAL",
        "category": "BILL_OVERDUE",
        "title": "BESCOM Electricity Bill Overdue",
        "subtitle": "₹2,000.00 was due 2 days ago",
        "action_label": "Record Payment",
        "navigation_target": "/bills/uuid-bill-1"
      },
      {
        "id": "uuid-task-2",
        "severity": "CRITICAL",
        "category": "TASK_OVERDUE",
        "title": "Clean Water Filter Overdue",
        "subtitle": "Assigned to Vivek • Due yesterday",
        "action_label": "Complete Task",
        "navigation_target": "/tasks/uuid-task-2"
      },
      {
        "id": "uuid-inv-3",
        "severity": "HIGH",
        "category": "STOCK_EMPTY",
        "title": "Basmati Rice is Out of Stock",
        "subtitle": "0 kg remaining in Pantry",
        "action_label": "Add to Purchase List",
        "navigation_target": "/inventory/uuid-inv-3"
      }
    ]
  }
  ```
