# Ozhzo Verse — Phase 7: Unified Home Dashboard Specification

## 1. Concept & Product Goal
The Home Dashboard is the primary landing experience of Ozhzo Verse. It provides an immediate, unified operational pulse answering:
**"WHAT IS HAPPENING IN MY HOME RIGHT NOW?"**

It replaces fragmented module links with a coherent, priority-ranked domestic command center.

---

## 2. Dashboard Information Architecture & Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🏠 MADHAVAN HOME                         [ Home Switcher ▾ ] [ Vivek M. 👤 ] │
│ Good morning, Vivek • Friday, 15 August 2026                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🚨 ATTENTION NEEDED (3 ITEMS)                                               │
│ ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────┐ │
│ │ ⚡ Overdue Bill: BESCOM  │ │ 🧹 Overdue: Water Filter│ │ 🍚 Low: Basmati │ │
│ │    ₹2,000.00 • 2d ago   │ │    Assigned: Vivek      │ │    3 kg / 10 kg │ │
│ └─────────────────────────┘ └─────────────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ 📅 TODAY AT A GLANCE                                                        │
│ 09:00 AM  🎂 Grandmother's 80th Birthday (Family Gathering)                 │
│ 10:30 AM  🩺 Doctor Appointment — City Clinic (Karthika)                    │
│ 06:00 PM  ⚡ BESCOM Electricity Bill Due (₹2,000.00)                       │
│ 07:00 PM  🧹 Task Due: Clean Water Filter (Vivek)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ ➕ GLOBAL QUICK ADD                                                         │
│ [ + Task ] [ + Shopping Item ] [ + Inventory ] [ + Asset ] [ + Bill ] [ + Event ] │
├─────────────────────────────────────────────────────────────────────────────┤
│ 📊 HOME HEALTH & STATUS                                                     │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│ │ 🛒 Purchase  │ │ 🧹 Chores    │ │ ⚡ Unpaid    │ │ 📦 Assets Borrowed   │ │
│ │    4 Items   │ │    3 Active  │ │    ₹3,136.00 │ │    1 Item (Drill)    │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ ⚡ RECENT ACTIVITY                                                          │
│ • Vivek marked Basmati Rice (5kg) purchased → Stock added to Pantry (10m ago)│
│ • Karthika completed task "Service AC Filter" (2h ago)                       │
│ • Vivek recorded payment ₹2,137 for Electricity Bill (Yesterday)            │
│ • Vivek borrowed Electric Drill from Garage → Tool Cabinet (3d ago)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Aggregation & Priority Ordering Rules

The dashboard endpoint `GET /api/v1/homes/{home_id}/dashboard` executes coordinated queries in parallel:

1. **Attention Items (Ranked by Severity)**:
   - `CRITICAL` (Red): Overdue Bills, Overdue Tasks.
   - `HIGH` (Amber): Bills Due Today, Tasks Due Today, Out of Stock Supplies.
   - `NORMAL` (Yellow): Low Stock Supplies, Overdue Asset Returns.
   - `INFO` (Blue): Events happening today, pending invitations.
2. **Today Timeline**:
   - Merges Events, Tasks due today, Bills due today sorted by `start_time` / `due_date`.
3. **Status Summary KPIs**:
   - `active_tasks_count`, `unpaid_bills_amount`, `low_stock_items_count`, `purchase_items_count`, `borrowed_assets_count`.
4. **Recent Activity**:
   - Latest 5 entries aggregated from `stock_movements`, `tasks (completed_at)`, `bill_payments`, `asset_loans`.

---

## 4. UI States & Edge Cases

| State | Visual Representation & Recovery Action |
|---|---|
| **Empty Home (New User)** | Warm onboarding welcome card: *"Your home is ready! Let's add your first pantry item, bill, or family chore."* with guided Quick Start buttons. |
| **All Clear (Zero Attention)** | Green check badge: *"Everything in your home is up to date!"* |
| **Network Error / Retry** | Graceful error card with *"Failed to load dashboard. [Retry]"* button; avoids white-screen crash. |
| **Multi-Home Switching** | Instant re-fetch upon changing active Home in header dropdown. |
