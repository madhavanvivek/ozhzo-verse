# Ozhzo Verse — Phase 3B: Shopping API Specification

## 1. Base URL & Security Headers
All endpoints are scoped under the Home tenant context:
```
BASE_URL: /api/v1/homes/{home_id}/shopping
Headers:
  Authorization: Bearer <access_token>
```
Every endpoint validates `require_home_permission(...)`.

---

## 2. API Endpoints Specification

### 2.1 Shopping Lists API
- `GET /homes/{home_id}/shopping/lists`: Retrieves all shopping lists for the Home with total and pending counts.
- `POST /homes/{home_id}/shopping/lists`: Creates a custom list (e.g. "Weekly Costco Run").
- `GET /homes/{home_id}/shopping/lists/{list_id}`: Retrieves specific list metadata.
- `PATCH /homes/{home_id}/shopping/lists/{list_id}`: Updates name, icon, or sort order.
- `DELETE /homes/{home_id}/shopping/lists/{list_id}`: Deletes custom list.

---

### 2.2 Shopping Items API
- `GET /homes/{home_id}/shopping/items`:
  - Query Filters: `list_id`, `status` (`ADDED`, `IN_CART`, `PURCHASED`, `SUGGESTED`), `priority` (`LOW`, `NORMAL`, `HIGH`), `source`, `assigned_to`, `search`, `page`, `page_size`.
  - Response: Paginated list of shopping items with assigned member names and inventory links.

- `POST /homes/{home_id}/shopping/items`:
  - Request Body:
    ```json
    {
      "list_id": "uuid",
      "inventory_item_id": "uuid (optional)",
      "category_id": "uuid (optional)",
      "name": "Sunflower Cooking Oil",
      "quantity": 2.0,
      "unit": "L",
      "priority": "HIGH",
      "source": "MANUAL",
      "assigned_to": "uuid (optional)",
      "expected_price": 14.99,
      "notes": "Prefer cold pressed"
    }
    ```

- `PATCH /homes/{home_id}/shopping/items/{item_id}`: Partial update (quantity, unit, priority, notes, version for optimistic locking).
- `DELETE /homes/{home_id}/shopping/items/{item_id}`: Removes item from shopping list.

---

### 2.3 Replenishment & Suggestions API
- `GET /homes/{home_id}/shopping/suggestions`:
  - Scans `inventory_items` where `status IN ('LOW', 'OUT_OF_STOCK')` that are not already active on a shopping list.
  - Returns calculated `suggested_quantity` for each item:
    $$\text{suggested\_quantity} = \text{preferred\_quantity} - \text{quantity}$$
  - Response: List of suggested items with one-click conversion payloads.

- `POST /homes/{home_id}/shopping/convert-suggestion`:
  - Request:
    ```json
    {
      "inventory_item_id": "uuid",
      "list_id": "uuid (optional, defaults to primary)",
      "quantity": 8.0,
      "priority": "HIGH"
    }
    ```
  - Creates shopping item with `source = 'LOW_STOCK'` or `'OUT_OF_STOCK'`.

---

### 2.4 Purchase & Restock Workflow API
- `POST /homes/{home_id}/shopping/items/{item_id}/purchase`:
  - Request:
    ```json
    {
      "actual_price": 12.50,
      "store_name": "Trader Joe's",
      "restock_inventory": true,
      "purchased_quantity": 2.0,
      "version": 1,
      "notes": "Bought 2x 1L bottles"
    }
    ```
  - Validates `version` concurrency lock.
  - If `restock_inventory == true` and `inventory_item_id` is set:
    - Atomically increments `inventory_items.quantity`.
    - Creates `stock_movements` with `movement_type = 'PURCHASE'`.
  - Appends `purchase_records` entry.
  - Updates `shopping_item.status = 'PURCHASED'`.

- `POST /homes/{home_id}/shopping/items/{item_id}/assign`:
  - Request: `{ "assigned_to": "uuid" }`
  - Assigns shopping item to family member.

---

### 2.5 Purchase History API
- `GET /homes/{home_id}/shopping/history`:
  - Query Filters: `start_date`, `end_date`, `purchased_by`, `search`, `page`, `page_size`.
  - Response: Chronological ledger of all historical completed purchases.

- `GET /homes/{home_id}/shopping/summary`:
  - Response: Real-time counts (`total_pending`, `high_priority_count`, `low_stock_suggestions_count`, `in_cart_count`, `recent_purchases_count`).
