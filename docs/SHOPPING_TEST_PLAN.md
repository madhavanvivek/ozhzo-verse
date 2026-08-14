# Ozhzo Verse — Phase 3B: Shopping & Auto-Replenishment Test Plan

## 1. Scope & Strategy
This test plan provides comprehensive automated coverage for the collaborative household shopping engine, replenishment derivation, restock transactions, optimistic concurrency, and multi-tenant security isolation.

---

## 2. Test Suite Matrix

### 2.1 Shopping Item CRUD & Lists
1. **List Creation & Auto-Provisioning**: Verify that a default "Main Shopping List" is automatically provisioned for a newly created Home.
2. **Manual Shopping Item Addition**: Create items with high-precision quantities (`2.500 kg`), priorities (`HIGH`), and notes.
3. **Shopping-Only Items**: Create items with `inventory_item_id = NULL` (e.g. "Birthday gift").
4. **Member Assignment**: Assign shopping items to a specific family member and verify filter retrieval.

### 2.2 Replenishment & Suggestions Engine
5. **Low Stock Detection & Derivation**:
   - Inventory item with `current = 2.0`, `min = 5.0`, `preferred = 10.0`.
   - Verify suggestion endpoint calculates `suggested_quantity = 8.0`.
6. **Fallback Derivation**:
   - Inventory item with `current = 0`, `min = 2.0`, `preferred = NULL`.
   - Verify fallback calculation yields `suggested_quantity = 4.0`.
7. **One-Tap Conversion**: Accept suggestion; verify shopping item created with `source = 'LOW_STOCK'`.
8. **Duplicate Suggestion Filtering**: Item already active on a shopping list is excluded from suggestions.

### 2.3 Purchase & Inventory Restock Integration
9. **Purchase with Inventory Restock Confirmed**:
   - Shopping item linked to Inventory Rice (`2.0 kg`).
   - Mark as `PURCHASED` with `restock_inventory = True` and `purchased_quantity = 8.0 kg`.
   - Verify:
     - `inventory_items.quantity` increases to `10.0 kg`.
     - `inventory_items.status` transitions from `LOW` to `GOOD`.
     - `stock_movements` record created with `movement_type = 'PURCHASE'`.
     - `purchase_records` entry created.
10. **Purchase without Inventory Restock**:
    - Mark as `PURCHASED` with `restock_inventory = False`.
    - Verify `inventory_items.quantity` remains unchanged.
11. **Shopping-Only Item Purchase**: Purchase shopping item without `inventory_item_id`; verify clean `purchase_records` creation without stock movements error.

### 2.4 Concurrency & Duplicate Prevention
12. **Optimistic Locking Guard**:
    - Member A and Member B attempt to checkout the same item version.
    - First checkout succeeds; second returns HTTP 409 Conflict.
13. **Double Purchase Prevention**:
    - Attempting to purchase an already purchased item returns HTTP 400 Bad Request.

### 2.5 Security & Multi-Home Isolation
14. **Cross-Home Shopping Access**: User in Home A cannot read, add, or checkout Home B shopping items (HTTP 403 Forbidden).
15. **Unverified Mobile Account Rejection**: Unverified accounts cannot create or purchase items.
16. **Role Permission Enforcement**: Active members can collaborate; non-members receive HTTP 403.
