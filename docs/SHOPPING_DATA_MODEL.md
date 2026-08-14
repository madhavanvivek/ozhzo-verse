# Ozhzo Verse — Phase 3B: Shopping Data Model

## 1. Relational DDL Schema

```sql
-- 1. Shopping Categories (Configurable)
CREATE TABLE IF NOT EXISTS shopping_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_shopping_categories_home_name UNIQUE (home_id, name)
);

-- 2. Shopping Lists
CREATE TABLE IF NOT EXISTS shopping_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    icon VARCHAR(50) NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Shopping List Items
CREATE TABLE IF NOT EXISTS shopping_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    list_id UUID NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
    inventory_item_id UUID NULL REFERENCES inventory_items(id) ON DELETE SET NULL,
    category_id UUID NULL REFERENCES shopping_categories(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    priority VARCHAR(16) NOT NULL DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH
    source VARCHAR(32) NOT NULL DEFAULT 'MANUAL', -- MANUAL, LOW_STOCK, OUT_OF_STOCK, RECURRING, RECOMMENDED
    status VARCHAR(32) NOT NULL DEFAULT 'ADDED', -- SUGGESTED, ADDED, IN_CART, PURCHASED, CANCELLED
    expected_price NUMERIC(10, 2) NULL,
    actual_price NUMERIC(10, 2) NULL,
    notes TEXT NULL,
    added_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    assigned_to UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_at TIMESTAMP WITH TIME ZONE NULL,
    restocked_to_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Purchase Records (Historical Purchase & Spending Ledger)
CREATE TABLE IF NOT EXISTS purchase_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    shopping_item_id UUID NULL REFERENCES shopping_items(id) ON DELETE SET NULL,
    inventory_item_id UUID NULL REFERENCES inventory_items(id) ON DELETE SET NULL,
    stock_movement_id UUID NULL REFERENCES stock_movements(id) ON DELETE SET NULL,
    item_name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    total_price NUMERIC(10, 2) NULL,
    unit_price NUMERIC(10, 2) NULL,
    store_name VARCHAR(120) NULL,
    purchased_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    restocked_to_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Indexing Strategy

```sql
-- Fast home-scoped list item queries by status
CREATE INDEX IF NOT EXISTS idx_shopping_items_home_list_status 
ON shopping_items (home_id, list_id, status);

-- Fast query for active shopping items
CREATE INDEX IF NOT EXISTS idx_shopping_items_active 
ON shopping_items (home_id, status) 
WHERE status IN ('ADDED', 'IN_CART', 'SUGGESTED');

-- Fast purchase history timeline
CREATE INDEX IF NOT EXISTS idx_purchase_records_home_time 
ON purchase_records (home_id, purchased_at DESC);

-- Fast link query from inventory item
CREATE INDEX IF NOT EXISTS idx_shopping_items_inv_link 
ON shopping_items (inventory_item_id) 
WHERE inventory_item_id IS NOT NULL;
```

---

## 3. Data Dictionary

### `shopping_items`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` | Owning Home tenant (FK) |
| `list_id` | `UUID` | Target shopping list (FK) |
| `inventory_item_id` | `UUID` (Nullable) | Associated inventory item for auto-restock |
| `category_id` | `UUID` (Nullable) | Shopping category grouping |
| `name` | `VARCHAR(150)` | Item name (e.g. "Organic Whole Milk") |
| `quantity` | `NUMERIC(10, 3)` | Quantity to purchase (decimal precision) |
| `unit` | `VARCHAR(32)` | Unit of measurement (`L`, `kg`, `pcs`, `packs`) |
| `priority` | `VARCHAR(16)` | `LOW`, `NORMAL`, `HIGH` |
| `source` | `VARCHAR(32)` | `MANUAL`, `LOW_STOCK`, `OUT_OF_STOCK`, `RECURRING`, `RECOMMENDED` |
| `status` | `VARCHAR(32)` | `SUGGESTED`, `ADDED`, `IN_CART`, `PURCHASED`, `CANCELLED` |
| `expected_price` | `NUMERIC(10, 2)` | Estimated budget price |
| `actual_price` | `NUMERIC(10, 2)` | Actual checkout price |
| `added_by` | `UUID` | Member who added item |
| `assigned_to` | `UUID` | Member assigned to buy item |
| `purchased_by` | `UUID` | Member who executed purchase |
| `purchased_at` | `TIMESTAMP` | Timestamp of checkout |
| `restocked_to_inventory` | `BOOLEAN` | True if added to `inventory_items` on purchase |
| `version` | `INTEGER` | Optimistic locking version number |

### `purchase_records`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Purchase record PK |
| `home_id` | `UUID` | Home tenant (FK) |
| `shopping_item_id` | `UUID` | Source shopping item |
| `inventory_item_id` | `UUID` | Restocked inventory item |
| `stock_movement_id` | `UUID` | Generated `stock_movements` record |
| `item_name` | `VARCHAR(150)` | Item name |
| `quantity` & `unit` | `NUMERIC(10, 3)` / `VARCHAR(32)` | Purchased quantity & unit |
| `total_price` | `NUMERIC(10, 2)` | Total receipt expense |
| `store_name` | `VARCHAR(120)` | Store / supermarket name |
| `purchased_by` | `UUID` | Buyer member |
| `purchased_at` | `TIMESTAMP` | Purchase timestamp |
| `restocked_to_inventory` | `BOOLEAN` | Restock flag |
