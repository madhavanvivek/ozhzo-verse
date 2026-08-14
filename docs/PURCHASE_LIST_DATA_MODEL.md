# Ozhzo Verse — Phase 3B: Home Purchase List Data Model

## 1. Relational DDL Schema

```sql
-- 1. Home Purchase Items (Active List)
CREATE TABLE IF NOT EXISTS purchase_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    inventory_item_id UUID NULL REFERENCES inventory_items(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    notes TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, PURCHASED, CANCELLED
    added_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_at TIMESTAMP WITH TIME ZONE NULL,
    restocked_to_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 2. Purchase History (Immutable Completed Purchases Ledger)
CREATE TABLE IF NOT EXISTS purchase_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    purchase_item_id UUID NULL REFERENCES purchase_items(id) ON DELETE SET NULL,
    inventory_item_id UUID NULL REFERENCES inventory_items(id) ON DELETE SET NULL,
    stock_movement_id UUID NULL REFERENCES stock_movements(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    purchased_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    restocked_to_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Performance & Indexing Strategy

```sql
-- Fast Home-scoped active list queries
CREATE INDEX IF NOT EXISTS idx_purchase_items_home_status 
ON purchase_items (home_id, status) 
WHERE deleted_at IS NULL;

-- Fast inventory link lookup
CREATE INDEX IF NOT EXISTS idx_purchase_items_inv_link 
ON purchase_items (home_id, inventory_item_id) 
WHERE inventory_item_id IS NOT NULL;

-- Fast purchase history timeline
CREATE INDEX IF NOT EXISTS idx_purchase_history_home_time 
ON purchase_history (home_id, purchased_at DESC);
```

---

## 3. Data Dictionary

### `purchase_items`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` | Owning Home tenant boundary (FK) |
| `inventory_item_id` | `UUID` (Nullable) | Optional link to inventory item for restock |
| `name` | `VARCHAR(150)` | Item name (e.g. "Milk", "Rice", "Screwdriver") |
| `quantity` | `NUMERIC(10, 3)` | Decimal quantity (default `1.000`) |
| `unit` | `VARCHAR(32)` | Unit of measurement (e.g. `L`, `kg`, `pcs`, `packs`) |
| `notes` | `TEXT` | Optional remarks (e.g. "Full cream", "Brand X preferred") |
| `status` | `VARCHAR(32)` | `PENDING`, `PURCHASED`, `CANCELLED` |
| `added_by` | `UUID` | Member who added the item |
| `purchased_by` | `UUID` | Member who marked the item as purchased |
| `purchased_at` | `TIMESTAMPTZ` | Timestamp when checked off |
| `restocked_to_inventory` | `BOOLEAN` | True if inventory quantity was updated |
| `version` | `INTEGER` | Concurrency lock version |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | Timestamps |

### `purchase_history`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Historical record PK |
| `home_id` | `UUID` | Home tenant (FK) |
| `purchase_item_id` | `UUID` | Reference to original purchase item |
| `inventory_item_id` | `UUID` | Reference to restocked inventory item (if applicable) |
| `stock_movement_id` | `UUID` | Reference to generated `stock_movements` record |
| `name` | `VARCHAR(150)` | Item name |
| `quantity` & `unit` | `NUMERIC(10, 3)` / `VARCHAR(32)` | Purchased quantity & measurement unit |
| `purchased_by` | `UUID` | Member who bought the item |
| `purchased_at` | `TIMESTAMPTZ` | Timestamp of purchase |
| `restocked_to_inventory` | `BOOLEAN` | True if added to inventory |
| `notes` | `TEXT` | Notes |
