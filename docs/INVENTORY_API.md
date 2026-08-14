# Ozhzo Verse — Phase 3A: Inventory & Asset API Specification

## 1. Base URL & Security
```
BASE_URL: /api/v1/homes/{home_id}/inventory
Headers:
  Authorization: Bearer <access_token>
```
Every route enforces `require_home_permission(...)`.

---

## 2. API Endpoints

### 2.1 Locations API
- `GET /api/v1/homes/{home_id}/locations`: Returns hierarchical tree and flat list with precomputed materialized paths.
- `POST /api/v1/homes/{home_id}/locations`: Creates a room, zone, cupboard, or box (`parent_id`, `name`, `location_type`, `icon`, `description`).
- `GET /api/v1/homes/{home_id}/locations/{location_id}`: Retrieves location details and list of all items/assets currently stored inside.
- `PATCH /api/v1/homes/{home_id}/locations/{location_id}`: Updates location name or moves entire location under another parent.
- `DELETE /api/v1/homes/{home_id}/locations/{location_id}`: Soft deletes location.

### 2.2 Items & Assets API
- `GET /api/v1/homes/{home_id}/inventory/items`:
  - Query filters: `item_type` (`CONSUMABLE`, `ASSET`), `location_id`, `category_id`, `status`, `asset_status`, `search`, `page`, `page_size`.
- `POST /api/v1/homes/{home_id}/inventory/items`: Creates item/asset with optional `location_id`, `condition`, `quantity`, `unit`, `min_threshold`.
- `GET /api/v1/homes/{home_id}/inventory/items/{item_id}`: Detailed item payload including computed location path and last seen info.
- `PATCH /api/v1/homes/{home_id}/inventory/items/{item_id}`: Updates item attributes.
- `DELETE /api/v1/homes/{home_id}/inventory/items/{item_id}`: Soft deletes item.

### 2.3 Physical Location Movements API
- `POST /api/v1/homes/{home_id}/inventory/items/{item_id}/move`:
  - Request: `{ "to_location_id": "uuid", "reason": "Moved to garage" }`
  - Records previous location, updates current location, appends to `location_movements`, and updates `last_seen_at` / `last_seen_by`.
- `GET /api/v1/homes/{home_id}/inventory/items/{item_id}/location-history`: Returns chronological location movement timeline.

### 2.4 Asset Lending & Borrowing API
- `POST /api/v1/homes/{home_id}/inventory/items/{item_id}/borrow`:
  - Request:
    ```json
    {
      "borrower_name": "Ashraf",
      "borrower_type": "EXTERNAL_PERSON",
      "borrower_contact": "+919876543210",
      "expected_return_at": "2026-08-20T18:00:00Z",
      "notes": "Borrowed for home repair"
    }
    ```
  - Validates asset is currently `AVAILABLE`. Transitions asset to `BORROWED`, records `asset_loans` entry, updates `current_holder_name`.
- `POST /api/v1/homes/{home_id}/inventory/items/{item_id}/return`:
  - Request:
    ```json
    {
      "return_location_id": "uuid",
      "notes": "Returned in perfect condition"
    }
    ```
  - Validates active loan exists. Sets loan to `RETURNED`, transitions asset status back to `AVAILABLE`, clears holder, and updates item location.
- `GET /api/v1/homes/{home_id}/inventory/items/{item_id}/loans`: Returns full borrowing history for the asset.
- `GET /api/v1/homes/{home_id}/inventory/loans`: Lists all currently borrowed or overdue assets in the Home.

### 2.5 Stock Movements API (For Consumables)
- `POST /api/v1/homes/{home_id}/inventory/items/{item_id}/movements`: Records `ADD`, `CONSUME`, `ADJUST`, `WASTE` and recalculates deterministic stock status.
- `GET /api/v1/homes/{home_id}/inventory/items/{item_id}/movements`: Returns consumption ledger.
- `GET /api/v1/homes/{home_id}/inventory/summary`: Returns summary metrics (`total_items`, `consumables_count`, `assets_count`, `low_stock_count`, `borrowed_assets_count`).
