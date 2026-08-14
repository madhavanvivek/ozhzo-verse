# Ozhzo Verse — Phase 3B: Home Purchase List API Specification

## 1. Base URL & Security Headers
All endpoints are scoped under the Home tenant context:
```
BASE_URL: /api/v1/homes/{home_id}/purchase-list
Headers:
  Authorization: Bearer <access_token>
```
Every endpoint validates `require_home_permission(...)`.

---

## 2. API Endpoints Specification

### 2.1 Active Purchase List Endpoints

#### `GET /api/v1/homes/{home_id}/purchase-list`
- **Permission**: `shopping:view`
- **Query Params**:
  - `status`: string (default `PENDING`, options: `PENDING`, `PURCHASED`, `CANCELLED`, `ALL`)
  - `search`: string (case-insensitive substring filter)
- **Response**: List of active purchase items with adder profile details.

#### `POST /api/v1/homes/{home_id}/purchase-list`
- **Permission**: `shopping:create`
- **Request Body**:
  ```json
  {
    "name": "Milk",
    "quantity": 2.0,
    "unit": "L",
    "notes": "Full cream",
    "inventory_item_id": null
  }
  ```

#### `PATCH /api/v1/homes/{home_id}/purchase-list/{item_id}`
- **Permission**: `shopping:edit`
- **Request Body**: Partial update for `name`, `quantity`, `unit`, `notes`, or `version`.

#### `DELETE /api/v1/homes/{home_id}/purchase-list/{item_id}`
- **Permission**: `shopping:delete`
- **Behavior**: Marks item `status = 'CANCELLED'` and sets `deleted_at = NOW()`.

---

### 2.2 Purchase Action & Inventory Restock

#### `POST /api/v1/homes/{home_id}/purchase-list/{item_id}/purchase`
- **Permission**: `shopping:purchase`
- **Request Body**:
  ```json
  {
    "restock_inventory": true,
    "purchased_quantity": 2.0,
    "notes": "Bought at supermarket"
  }
  ```
- **Behavior**:
  1. Validates item is currently `PENDING`.
  2. Sets item `status = 'PURCHASED'`, `purchased_by = current_user.id`, `purchased_at = NOW()`.
  3. Appends an entry to `purchase_history`.
  4. If `restock_inventory == true` and `inventory_item_id` is set:
     - Increments `inventory_items.quantity += purchased_quantity`.
     - Recalculates stock status (`status = 'GOOD'`).
     - Appends an immutable `stock_movements` record of type `PURCHASE`.
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "item_id": "8f3b2c1a-...",
      "name": "Milk",
      "status": "PURCHASED",
      "restocked_to_inventory": true,
      "purchased_by": "user-uuid",
      "purchased_at": "2026-08-14T15:30:00Z"
    }
  }
  ```

---

### 2.3 Purchase History & Suggestions

#### `GET /api/v1/homes/{home_id}/purchase-history`
- **Permission**: `shopping:view`
- **Query Params**: `search`, `page` (default 1), `page_size` (default 20, max 100).
- **Response**: Chronological ledger of completed purchases.

#### `GET /api/v1/homes/{home_id}/purchase-list/suggestions`
- **Permission**: `shopping:view`
- **Response**: List of low-stock and out-of-stock pantry items not yet on the active purchase list, with suggested restock quantities.
