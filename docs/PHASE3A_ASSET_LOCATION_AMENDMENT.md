# Ozhzo Verse — Phase 3A Architecture Amendment: Inventory + Home Assets + Location Memory + Borrowing

**Document**: Phase 3A Architecture Amendment  
**Status**: PLANNING & ARCHITECTURE EXPANSION (Pre-Execution Gate)  

---

## 1. Updated Architecture Overview
Phase 3A unifies Pantry Consumables and Durable Household Assets under a single Home Items engine while introducing two dedicated sensory dimensions:
1. **Physical Location Hierarchy & Movement Ledger** (*"WHERE IS IT?"*)
2. **Asset Custody & Borrowing/Lending Ledger** (*"WHO HAS IT?"*)

### Architectural Separation of Concerns
The system maintains 3 completely independent event ledgers referencing `inventory_items`:
- **`stock_movements`**: Quantity adjustments (`ADD`, `CONSUME`, `ADJUST`, `PURCHASE`, `WASTE`).
- **`location_movements`**: Physical room/container moves (`from_location` $\rightarrow$ `to_location`).
- **`asset_loans`**: Custody lending transactions (`BORROW`, `RETURN`, `OVERDUE`).

---

## 2. Database Schema Changes

### 2.1 Enhancements to `inventory_items`
- `item_type VARCHAR(32) NOT NULL DEFAULT 'CONSUMABLE'` (`CONSUMABLE`, `ASSET`)
- `location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL`
- `location_path TEXT NULL` (Materialized path cache, e.g. `Store > 3rd Cupboard > Blue Box`)
- `condition VARCHAR(32) NULL` (`NEW`, `EXCELLENT`, `GOOD`, `FAIR`, `POOR`, `DAMAGED`)
- `asset_status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE'` (`AVAILABLE`, `BORROWED`, `MISSING`, `ARCHIVED`)
- `current_holder_name VARCHAR(120) NULL`
- `current_holder_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL`
- `last_seen_at TIMESTAMP WITH TIME ZONE NULL`
- `last_seen_by UUID NULL REFERENCES users(id) ON DELETE SET NULL`
- `last_seen_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL`

### 2.2 New Tables
1. **`locations`**: Hierarchical location tree (`id`, `home_id`, `parent_id`, `name`, `location_type`, `description`, `icon`, `sort_order`, `is_active`).
2. **`location_movements`**: Immutable relocation ledger (`id`, `home_id`, `item_id`, `from_location_id`, `to_location_id`, `from_location_path`, `to_location_path`, `reason`, `moved_by`, `moved_at`).
3. **`asset_loans`**: Immutable lending ledger (`id`, `home_id`, `item_id`, `borrower_type`, `borrower_user_id`, `borrower_name`, `borrower_contact`, `loan_status`, `borrowed_at`, `expected_return_at`, `returned_at`, `return_location_id`, `return_location_path`, `issued_by`, `received_by`, `notes`).

---

## 3. API Changes
- **Locations API**:
  - `GET /homes/{home_id}/locations` (Tree & flat list with paths)
  - `POST /homes/{home_id}/locations` (Create zone/container)
  - `GET /homes/{home_id}/locations/{location_id}` (Details & contained items list)
  - `PATCH /homes/{home_id}/locations/{location_id}`
  - `DELETE /homes/{home_id}/locations/{location_id}`
- **Items & Assets API**:
  - `GET /homes/{home_id}/inventory/items` (Supports filtering by `item_type`, `location_id`, `asset_status`, `holder`, text search)
  - `POST /homes/{home_id}/inventory/items` (Create Consumable or Asset with location)
  - `POST /homes/{home_id}/inventory/items/{item_id}/move` (Move to new location & create history)
  - `GET /homes/{home_id}/inventory/items/{item_id}/location-history` (Relocation timeline)
  - `POST /homes/{home_id}/inventory/items/{item_id}/borrow` (Issue loan to member or external person)
  - `POST /homes/{home_id}/inventory/items/{item_id}/return` (Accept return & specify return location)
  - `GET /homes/{home_id}/inventory/items/{item_id}/loans` (Borrowing history ledger)
  - `GET /homes/{home_id}/inventory/loans` (List active/overdue borrowed assets in Home)

---

## 4. UX & Client Changes

### Web (Next.js)
- **Unified Inventory & Asset Explorer**:
  - Toggle between `All Items`, `Pantry Consumables`, and `Household Assets`.
  - Location Tree Browser in sidebar: Click `Store > 3rd Cupboard > Blue Box` to see all items inside.
  - Quick action buttons on Asset rows: `[Move]`, `[Borrow]`, `[Return]`, `[History]`.
  - `Borrowed Assets` badge & filter tab.

### Mobile (Flutter)
- Quick Search bar with location matching (e.g. searching "Blue Box" displays all items inside).
- Quick Location Selector during item creation (drill-down cascading sheet).
- 1-Tap `[Move]` sheet and `[Borrow/Return]` bottom drawer.

---

## 5. Security Implications & Isolation
- **Strict Home Scoping**:
  - A user cannot assign an item in Home A to a location in Home B (returns `403 Forbidden`).
  - A user cannot borrow an asset in Home A unless authorized in Home A context.
- **Role Permission Enforcement**:
  - `inventory:view`: Read items, locations, and loan statuses.
  - `inventory:edit`: Move items, record stock usage, issue loans, accept returns.
  - `inventory:delete`: Archive items/assets and locations.

---

## 6. Testing Changes
Comprehensive additions to `services/api/tests/test_phase3a_inventory.py`:
- Hierarchical location creation & nested tree resolution.
- Cross-home location assignment prevention.
- Asset relocation & immutable `location_movements` record generation.
- Asset lending lifecycle: `AVAILABLE` $\rightarrow$ `BORROWED` $\rightarrow$ `RETURNED` $\rightarrow$ `AVAILABLE`.
- Double-borrowing rejection (cannot borrow an already borrowed asset).
- Returning to a new location updates item `location_id` and location history simultaneously.
- Search by location name and item contained in location.

---

## 7. Migration Implications
- Non-destructive DDL additions to `database/schema.sql`.
- Existing `inventory_items` records default to `item_type = 'CONSUMABLE'` and `asset_status = 'AVAILABLE'`.

---

## 8. Future Connected Home Compatibility
- Ownership model is preserved: The asset is permanently owned by `home_id`.
- Future Connected Home lending will simply set `borrower_type = 'CONNECTED_HOME'` and store `borrower_home_id` without transferring item ownership.

---

## 9. Recommended Implementation Order (Post-Approval)
1. Update `database/schema.sql` and `models.py` with `locations`, `location_movements`, `asset_loans`, and updated `inventory_items`.
2. Implement backend schemas and REST endpoints for Locations, Movements, and Loans.
3. Update contract generator (`scripts/generate_contracts.sh`) for TypeScript and Dart models.
4. Implement Next.js Web UI (Location Tree, Asset Cards, Move/Borrow Modals).
5. Implement Flutter Mobile screens (Location Picker, Quick Move, Quick Borrow).
6. Run full verification suite (`generate_contracts.sh`, `test.sh`, `lint.sh`, `build.sh`).
7. Publish `/docs/PHASE3A_ASSET_LOCATION_REPORT.md`.
