# Ozhzo Verse — Phase 3B: Home Purchase List Implementation Plan

**Phase**: Phase 3B — Home Purchase List (Simplified Architecture)  
**Status**: ARCHITECTURE & PLANNING GATE (No production code written yet)  

---

## 1. Purchase List Architecture
The **Home Purchase List** is a shared household board answering *“What do we need to buy for our Home?”*.
- **Tenant Scope**: The Purchase List is owned directly by the `Home`, not individual users.
- **Unified Stream**: Captures both routine consumables (milk, rice, cooking oil) and general household supplies (curtains, umbrella, tools, dad's gift).
- **Zero Friction**: Primary manual addition requires only Item Name, Quantity, and Unit.
- **3-State Lifecycle**: `PENDING` $\rightarrow$ `PURCHASED` (or `CANCELLED`).

---

## 2. Purchase Item Model
- **Table**: `purchase_items`
  - `id`: UUID (PK)
  - `home_id`: UUID (FK to `homes.id`)
  - `inventory_item_id`: UUID (Nullable, optional link to inventory)
  - `name`: VARCHAR(150) (e.g. "Milk", "Rice", "Screwdriver")
  - `quantity`: NUMERIC(10, 3) (Default `1.000`)
  - `unit`: VARCHAR(32) (e.g. `L`, `kg`, `pcs`, `packs`)
  - `notes`: TEXT (Optional)
  - `status`: VARCHAR(32) (`PENDING`, `PURCHASED`, `CANCELLED`)
  - `added_by`: UUID (FK to `users.id`)
  - `purchased_by`: UUID (FK to `users.id`, populated on purchase)
  - `purchased_at`: TIMESTAMPTZ (Timestamp of purchase)
  - `restocked_to_inventory`: BOOLEAN (True if stock was updated)
  - `version`: INTEGER (Optimistic concurrency control)
  - `created_at`, `updated_at`, `deleted_at`

---

## 3. Purchase History
- **Table**: `purchase_history`
  - Maintains an immutable historical log of every completed purchase for the Home.
  - Fields: `id`, `home_id`, `purchase_item_id`, `inventory_item_id`, `stock_movement_id`, `name`, `quantity`, `unit`, `purchased_by`, `purchased_at`, `restocked_to_inventory`, `notes`, `created_at`.
  - Never deleted when active purchase items are completed or cleared.

---

## 4. Home Collaboration
- Every verified member of a Home shares the same active Purchase List.
- When Karthika adds "Milk" and Vivek adds "Rice", both items are instantly visible to all family members with clear attribution (`Added by Karthika`, `Added by Vivek`).

---

## 5. Inventory Integration
- **Optional Suggestion Source**: Low-stock and out-of-stock pantry items appear as suggestions (*"Rice is running low [ Add to Purchase List ]"*).
- **Human Gatekeeping**: Low stock **never** automatically adds items to the list or creates purchases without human approval.
- **Restock Confirmation**: When an inventory-linked item is checked off as purchased, the user is prompted: *"Update Home Inventory? [YES] [NO]"*.
  - If YES: An atomic transaction creates a `stock_movements` record (`movement_type = 'PURCHASE'`) and increments `inventory_items.quantity`.
  - If NO: The item moves to history without altering inventory.

---

## 6. API Endpoints
- Base Route: `/api/v1/homes/{home_id}/purchase-list`
  - `GET /`: List active pending purchase items (with search & status filters).
  - `POST /`: Add new purchase item (Name, Quantity, Unit, optional Notes/Inventory ID).
  - `PATCH /{id}`: Update quantity, unit, notes, or name.
  - `DELETE /{id}`: Cancel/remove item from active list.
  - `POST /{id}/purchase`: Mark item as purchased (with `restock_inventory: boolean` toggle).
  - `GET /suggestions`: View low-stock pantry replenishment suggestions.
- Base Route: `/api/v1/homes/{home_id}/purchase-history`
  - `GET /`: Searchable chronological ledger of past purchases.

---

## 7. Web User Experience (Next.js)
- **Active Purchase List Card**:
  - Direct inline addition bar: `[ Item Name ] [ Qty ] [ Unit ] [ + Add to List ]`.
  - Interactive item rows with large checkboxes and member attribution.
  - Low-stock suggestion banner with 1-click `[ + Add ]`.
- **Purchase History Tab**:
  - Chronological timeline with search filter.

---

## 8. Mobile User Experience (Flutter)
- **Fast Purchase Screen**:
  - High-contrast checkboxes for single-tap completion while shopping in-store.
  - Simple bottom sheet for adding items on the go.
  - Restock prompt sheet upon checking off an inventory-linked item.

---

## 9. Security & Multi-Tenant Isolation
- Strict Home tenant validation on every operation (`require_home_permission("shopping:view" / "shopping:create" / "shopping:purchase")`).
- Users belonging to multiple Homes have strictly isolated lists per `home_id`.
- Unverified mobile accounts receive `403 Forbidden`.

---

## 10. Testing Strategy
- 14-point automated test suite covering:
  - Manual additions and multi-member shared visibility
  - Low-stock suggestions detection and 1-tap conversion
  - Purchase checkout with confirmed inventory restock (updating `inventory_items`, `stock_movements`, and `purchase_history`)
  - Purchase without inventory restock
  - General non-inventory item checkout
  - Cancellation and purchase history preservation
  - Cross-home access rejection (403 Forbidden)

---

## 11. Future Auto-Replenishment Boundary
- Schema leaves clean hooks for:
  - Category, priority, and assigned shopper delegation
  - Store/price tracking and receipt uploads
  - Recurring scheduled additions
  - AI predictive consumption recommendations
- None of these are forced into the MVP baseline, preserving a lightweight, ultra-fast user experience.
