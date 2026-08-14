# Ozhzo Verse — Phase 3B: Home Purchase List Architecture

## 1. Architectural Philosophy
The **Home Purchase List** provides a frictionless, collaborative household board answering:
*“What do we need to buy for our Home?”*

Unlike personal shopping checklists, the Purchase List is owned directly by the **Home tenant**, enabling all family members to add supplies, view real-time needs, and check off items when shopping.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       HOME PURCHASE LIST FOUNDATION                     │
│                                                                         │
│  ┌──────────────────────┐                     ┌──────────────────────┐  │
│  │   MANUAL ADDITION    │                     │  LOW-STOCK PANTRY    │  │
│  │ (e.g. Milk, Curtains)│                     │ (Optional Suggestion)│  │
│  └──────────┬───────────┘                     └──────────┬───────────┘  │
│             │                                            │              │
│             │            ┌──────────────────────┐        │ [Add]        │
│             └──────────► │  HOME PURCHASE LIST  │ ◄──────┘              │
│                          │ (Shared Active Items)│                       │
│                          └──────────┬───────────┘                       │
│                                     │                                   │
│                           Member Checks Off Item                        │
│                                     │                                   │
│                                     ▼                                   │
│                          ┌──────────────────────┐                       │
│                          │  PURCHASE CONFIRMED  │                       │
│                          │ (Captured in History)│                       │
│                          └──────────┬───────────┘                       │
│                                     │                                   │
│                      Linked to Inventory Item?                          │
│                                     │                                   │
│                     ┌───────────────┴───────────────┐                   │
│                     ▼                               ▼                   │
│                 [ YES ]                          [ NO ]                 │
│         Prompt: "Update Inventory?"       (Purchase-Only Item)          │
│                     │                               │                   │
│          ┌──────────┴──────────┐                    │                   │
│          ▼                     ▼                    │                   │
│       [ YES ]               [ NO ]                  │                   │
│   Create PURCHASE      Retain in History            │                   │
│   Stock Movement         Without Stock              │                   │
│  & Increase Qty             Movement                │                   │
│          │                     │                    │                   │
│          └─────────────────────┴────────────────────┘                   │
│                                │                                        │
│                                ▼                                        │
│                     ┌──────────────────────┐                            │
│                     │   PURCHASE HISTORY   │                            │
│                     │  (Searchable Ledger) │                            │
│                     └──────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Pillars

1. **Home-Level Tenant Ownership**: The Purchase List is shared across all verified Home members. No member operates in a personal silo.
2. **Frictionless Manual Entry**: Adding an item requires only `name`, `quantity`, and `unit`. All other attributes (notes, category, priority, price) are optional.
3. **Optional Inventory Suggestions**: Low-stock pantry items appear as gentle suggestions (*"Rice is running low [ Add to Purchase List ]"*). The system **never** automatically purchases or forces items into the list without human confirmation.
4. **General & Inventory-Linked Items**: Items may exist independently (e.g. "School Project Paint", "Birthday Gift for Dad") or link to an `inventory_item_id` for automated stock replenishment upon checkout.
5. **Explicit Restock Confirmation**: Checking off an inventory-linked item prompts: *"Update Home Inventory?"*. Only when the user confirms is an atomic `stock_movements` record created and the inventory quantity updated.
6. **Immutable Purchase History**: Completed purchases move into a permanent, searchable history ledger (`purchase_history`), maintaining complete historical visibility.
7. **Simplified 3-State Lifecycle**:
   - `PENDING`: Active on the household purchase list.
   - `PURCHASED`: Bought and archived to history.
   - `CANCELLED`: Dismissed or removed.
