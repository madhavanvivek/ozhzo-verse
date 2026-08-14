# Ozhzo Verse — Phase 3A: Inventory & Asset Data Model

## 1. Complete Relational DDL Schema

```sql
-- 1. Inventory Categories
CREATE TABLE IF NOT EXISTS inventory_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inventory_categories_home_name UNIQUE (home_id, name)
);

-- 2. Hierarchical Locations
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    parent_id UUID NULL REFERENCES locations(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    location_type VARCHAR(32) NOT NULL DEFAULT 'ZONE', -- ROOM, ZONE, FURNITURE, CONTAINER, SHELF, HOOK, VEHICLE, OTHER
    description TEXT NULL,
    icon VARCHAR(50) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT uq_locations_home_parent_name UNIQUE (home_id, parent_id, name)
);

-- 3. Unified Inventory Items & Household Assets
CREATE TABLE IF NOT EXISTS inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    category_id UUID NULL REFERENCES inventory_categories(id) ON DELETE SET NULL,
    location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    item_type VARCHAR(32) NOT NULL DEFAULT 'CONSUMABLE', -- CONSUMABLE, ASSET
    name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    quantity NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    min_threshold NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    preferred_quantity NUMERIC(10, 3) NULL,
    max_quantity NUMERIC(10, 3) NULL,
    location_path TEXT NULL, -- Materialized path cache e.g. "Store > 3rd Cupboard > Blue Box"
    condition VARCHAR(32) NULL, -- NEW, EXCELLENT, GOOD, FAIR, POOR, DAMAGED
    asset_status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE', -- AVAILABLE, BORROWED, MISSING, ARCHIVED
    current_holder_name VARCHAR(120) NULL,
    current_holder_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE NULL,
    last_seen_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    last_seen_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    expiry_date DATE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'GOOD', -- GOOD, LOW_STOCK, OUT_OF_STOCK, EXPIRED
    notes TEXT NULL,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 4. Stock Movements (Consumption Ledger)
CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    movement_type VARCHAR(32) NOT NULL, -- ADD, CONSUME, ADJUST, PURCHASE, WASTE, RETURN
    quantity_delta NUMERIC(10, 3) NOT NULL,
    previous_quantity NUMERIC(10, 3) NOT NULL,
    resulting_quantity NUMERIC(10, 3) NOT NULL,
    reason TEXT NULL,
    performed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Location Movements (Relocation Ledger)
CREATE TABLE IF NOT EXISTS location_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    from_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    to_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    from_location_path TEXT NULL,
    to_location_path TEXT NOT NULL,
    reason TEXT NULL,
    moved_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    moved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Asset Lending & Borrowing Ledger
CREATE TABLE IF NOT EXISTS asset_loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    borrower_type VARCHAR(32) NOT NULL DEFAULT 'MEMBER', -- MEMBER, EXTERNAL_PERSON, CONNECTED_HOME
    borrower_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    borrower_name VARCHAR(120) NOT NULL,
    borrower_contact VARCHAR(100) NULL,
    loan_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, RETURNED, OVERDUE, LOST
    borrowed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expected_return_at TIMESTAMP WITH TIME ZONE NULL,
    returned_at TIMESTAMP WITH TIME ZONE NULL,
    return_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    return_location_path TEXT NULL,
    issued_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    received_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Indexing Strategy

```sql
-- Fast Home-scoped listing & status filtering
CREATE INDEX IF NOT EXISTS idx_inv_items_home_type_status 
ON inventory_items (home_id, item_type, asset_status) 
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_inv_items_home_loc 
ON inventory_items (home_id, location_id) 
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_locations_home_parent 
ON locations (home_id, parent_id) 
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_location_movements_item_time 
ON location_movements (item_id, moved_at DESC);

CREATE INDEX IF NOT EXISTS idx_asset_loans_item_time 
ON asset_loans (item_id, borrowed_at DESC);

CREATE INDEX IF NOT EXISTS idx_asset_loans_home_status 
ON asset_loans (home_id, loan_status);
```
