# Ozhzo Verse — Phase 3A: Inventory, Home Assets, Locations & Borrowing Implementation Plan

**Phase**: Phase 3A — Inventory + Home Assets + Location Memory + Borrowing  
**Status**: ARCHITECTURE & PLANNING GATE (No production code written yet)  

---

## 1. Existing Architecture Inspection & Reuse
- Reused Core Entities: `users` (Identity/Auth), `homes` (Primary Tenant Boundary), `home_members` (RBAC), `audit_logs` (System Audits), `require_home_permission` (Tenant Security Dependency).
- Zero Duplicate Infrastructure: All asset and location capabilities extend existing Home boundaries.

---

## 2. Proposed Entities & Schema Extensions
1. **`inventory_categories`**: `id`, `home_id`, `name`, `icon`, `color`, `sort_order`.
2. **`locations`**: Hierarchical physical locations (`id`, `home_id`, `parent_id`, `name`, `location_type`, `description`, `icon`, `sort_order`, `is_active`).
3. **`inventory_items`**: Unified items and assets (`id`, `home_id`, `category_id`, `location_id`, `item_type` [`CONSUMABLE`/`ASSET`], `name`, `description`, `quantity`, `unit`, `min_threshold`, `preferred_quantity`, `max_quantity`, `location_path`, `condition`, `asset_status` [`AVAILABLE`/`BORROWED`/`MISSING`/`ARCHIVED`], `current_holder_name`, `current_holder_user_id`, `last_seen_at`, `last_seen_by`, `last_seen_location_id`, `expiry_date`, `status`, `notes`, `created_by`, `created_at`, `updated_at`, `deleted_at`).
4. **`stock_movements`**: Immutable consumption ledger (`id`, `home_id`, `item_id`, `movement_type`, `quantity_delta`, `previous_quantity`, `resulting_quantity`, `reason`, `performed_by`, `created_at`).
5. **`location_movements`**: Immutable relocation ledger (`id`, `home_id`, `item_id`, `from_location_id`, `to_location_id`, `from_location_path`, `to_location_path`, `reason`, `moved_by`, `moved_at`).
6. **`asset_loans`**: Immutable lending & custody ledger (`id`, `home_id`, `item_id`, `borrower_type`, `borrower_user_id`, `borrower_name`, `borrower_contact`, `loan_status`, `borrowed_at`, `expected_return_at`, `returned_at`, `return_location_id`, `return_location_path`, `issued_by`, `received_by`, `notes`).

---

## 3. API Changes
- **Locations API**:
  - `GET /homes/{home_id}/locations`
  - `POST /homes/{home_id}/locations`
  - `GET /homes/{home_id}/locations/{id}`
  - `PATCH /homes/{home_id}/locations/{id}`
  - `DELETE /homes/{home_id}/locations/{id}`
- **Items & Assets API**:
  - `GET /homes/{home_id}/inventory/items` (Filters: `item_type`, `location_id`, `asset_status`, `search`)
  - `POST /homes/{home_id}/inventory/items`
  - `GET /homes/{home_id}/inventory/items/{id}`
  - `PATCH /homes/{home_id}/inventory/items/{id}`
  - `DELETE /homes/{home_id}/inventory/items/{id}`
- **Movement & Lending API**:
  - `POST /homes/{home_id}/inventory/items/{id}/move`
  - `GET /homes/{home_id}/inventory/items/{id}/location-history`
  - `POST /homes/{home_id}/inventory/items/{id}/borrow`
  - `POST /homes/{home_id}/inventory/items/{id}/return`
  - `GET /homes/{home_id}/inventory/items/{id}/loans`
  - `GET /homes/{home_id}/inventory/loans`
  - `POST /homes/{home_id}/inventory/items/{id}/movements` (Stock quantity)
  - `GET /homes/{home_id}/inventory/items/{id}/movements`
  - `GET /homes/{home_id}/inventory/summary`

---

## 4. Web Changes (Next.js)
- Unified Item & Asset Dashboard with Category and Location hierarchy trees.
- Fast Search with location lookup (`"Blue Box"` $\rightarrow$ reveals items inside).
- Modals for Quick Move, Quick Borrow, and Return to Location.

---

## 5. Mobile Changes (Flutter)
- Location Picker cascading bottom sheet.
- Swipe gestures for Quick Consume / Quick Relocate.
- Asset status indicators (`🟢 Available`, `🟡 Borrowed`).

---

## 6. Permission Model
- `inventory:view`: Read items, locations, loans, and movements.
- `inventory:create`: Create items, assets, categories, locations.
- `inventory:edit`: Update stock, move items, borrow/return assets.
- `inventory:delete`: Archive items, assets, locations.

---

## 7. Future Connected Home Compatibility
- Permanent ownership remains with `home_id`. Future Connected Home lending will reference `borrower_type = 'CONNECTED_HOME'` without changing underlying asset ownership.

---

## 8. Execution Sequence (Upon Approval)
1. Schema & SQLAlchemy ORM model updates (`database/schema.sql` and `models.py`).
2. Implement backend schemas and API routers (`locations.py`, `inventory.py`).
3. Update contract generator (`generate_contracts.sh`) for TS and Dart models.
4. Build Next.js Web interface components.
5. Build Flutter Mobile screens.
6. Run full verification suite (`generate_contracts.sh`, `test.sh`, `lint.sh`, `build.sh`).
7. Publish `/docs/PHASE3A_ASSET_LOCATION_REPORT.md`.
