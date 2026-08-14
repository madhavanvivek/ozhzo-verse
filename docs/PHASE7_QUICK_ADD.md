# Ozhzo Verse — Phase 7: Global Quick Add Interaction Framework

## 1. Concept & Interaction Architecture
The **Global Quick Add** component allows any authorized household member to record information immediately from anywhere in the app without navigating between separate modules first.

```
       ┌────────────────────────────────────────────────────────┐
       │                       ➕ QUICK ADD                      │
       ├────────────────────────────────────────────────────────┤
       │  🧹  Task            ──►  "Clean Water Filter"          │
       │  🛒  Shopping Item   ──►  "Basmati Rice (5 kg)"         │
       │  📦  Pantry Stock    ──►  "Olive Oil (1 L)"             │
       │  🔧  Home Asset      ──►  "Bosch Electric Drill"        │
       │  ⚡  Bill            ──►  "BESCOM Electricity (₹2,000)" │
       │  🎂  Family Event    ──►  "Doctor Appointment (10 AM)" │
       └────────────────────────────────────────────────────────┘
```

---

## 2. API Integration Mapping (Zero Duplication)

Global Quick Add does **not** create a new generic entity; it routes directly to the established domain endpoints:

| Action | Target Endpoint | Minimum Required Payload | RBAC Permission Required |
|---|---|---|---|
| **Add Task** | `POST /homes/{id}/tasks` | `title`, `priority` (default `NORMAL`), `due_date` (optional) | `tasks:create` |
| **Add Purchase Item** | `POST /homes/{id}/purchase-list/items` | `name`, `quantity` (default 1), `unit` (default `pcs`) | `purchases:create` |
| **Add Inventory Item** | `POST /homes/{id}/inventory/items` | `name`, `item_type: 'CONSUMABLE'`, `quantity`, `unit`, `location_id` | `inventory:create` |
| **Add Asset** | `POST /homes/{id}/inventory/items` | `name`, `item_type: 'ASSET'`, `location_id` | `inventory:create` |
| **Add Bill** | `POST /homes/{id}/bills` | `title`, `expected_amount`, `due_date` | `bills:create` |
| **Add Event** | `POST /homes/{id}/events` | `title`, `start_time`, `end_time`, `is_all_day` | `calendar:create` |

---

## 3. Client Interaction & UX Behavior

1. **Web App**:
   - Prominent `+ Add` button in the sticky top header bar.
   - Clicking opens a sleek unified action modal with tabs for each entity type.
   - Successful creation shows a toast notification: *"Task 'Clean AC' created."* with an optional `[View Task]` action link.
2. **Mobile App**:
   - Universal floating action button (FAB) `+` in bottom navigation.
   - Long-press or tap displays an animated radial/bottom sheet menu with quick action icons.
   - Keyboard auto-focuses on input title immediately for sub-3-second creation.
