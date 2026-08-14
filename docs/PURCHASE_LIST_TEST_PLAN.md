# Ozhzo Verse — Phase 3B: Home Purchase List Test Plan

## 1. Scope & Strategy
This test plan provides comprehensive automated test coverage for the collaborative Home Purchase List, manual additions, low-stock suggestions, purchase-to-inventory restock flows, purchase history, and tenant security.

---

## 2. Test Suite Matrix

### 2.1 Item Addition & Collaboration
1. **Manual Purchase Item Addition**: Create items with high-precision decimal quantity (`2.000 L`, `5.000 kg`) and optional notes.
2. **General Household Item Creation**: Create items with `inventory_item_id = NULL` (e.g. "Screwdriver", "Curtains").
3. **Multi-Member Collaborative Visibility**:
   - Member A adds "Milk".
   - Member B adds "Rice".
   - Both members query `/purchase-list` and retrieve the combined household list with `added_by` profile details.

### 2.2 Low-Stock Suggestions Integration
4. **Low Stock Detection & Suggestion**:
   - Create inventory item with `quantity = 2.0`, `min_threshold = 5.0`.
   - Query `/purchase-list/suggestions` and verify item appears with recommended restock quantity.
5. **Accepting Suggestion**:
   - Convert suggestion to a purchase list item; verify it appears as `PENDING` linked to `inventory_item_id`.
6. **Dismissing / Ignoring Suggestion**:
   - Verify unaccepted suggestions do not alter active purchase list or inventory.

### 2.3 Purchase Execution & Restock Workflows
7. **Purchase with Inventory Restock Confirmed**:
   - Purchase item linked to inventory item (`Rice 2.0 kg`).
   - Mark as `PURCHASED` with `restock_inventory = True` and `purchased_quantity = 5.0 kg`.
   - Verify:
     - Item status transitions from `PENDING` to `PURCHASED`.
     - `inventory_items.quantity` increases to `7.0 kg`.
     - `stock_movements` record created with `movement_type = 'PURCHASE'`.
     - `purchase_history` entry created with `purchased_by` and timestamp.
8. **Purchase without Inventory Restock**:
   - Mark as `PURCHASED` with `restock_inventory = False`.
   - Verify `inventory_items.quantity` is unchanged, while item moves to `purchase_history`.
9. **General Item Purchase**:
   - Mark a non-inventory item (`Screwdriver`) as `PURCHASED`.
   - Verify clean transition to `purchase_history` without stock movement errors.

### 2.4 Cancellation & History Ledger
10. **Cancel / Remove Item**: Delete item; verify status transitions to `CANCELLED` and is hidden from active list.
11. **Purchase History Retrieval**:
    - Query `/purchase-history` and verify historical entries are sorted chronologically and searchable.
    - Verify history is preserved when active list is empty.

### 2.5 Security & Multi-Home Tenant Isolation
12. **Cross-Home Access Rejection**: User in Home A cannot view, add to, or purchase from Home B purchase list (HTTP 403 Forbidden).
13. **Unverified Mobile Rejection**: Unverified accounts cannot add or purchase items.
14. **Double Purchase Prevention**: Attempting to purchase an already purchased item returns HTTP 400 Bad Request.
