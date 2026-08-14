# Ozhzo Verse — Hierarchical Location Memory

## 1. Overview
The Ozhzo Verse Location System provides a structured, hierarchical physical location model for each Home, answering *"WHERE IS IT?"* with pinpoint precision without requiring users to type repetitive long strings.

---

## 2. Location Tree Structure

A Location in Ozhzo Verse can have a `parent_id`, forming a self-referential tree within a Home:

```
HOME (Madhavan Home)
 ├── Entrance
 │    └── Key Holder
 │         └── Top Hook
 ├── Store Room
 │    └── 3rd Cupboard
 │         ├── Blue Box (Toolkit, Screwdrivers)
 │         └── Black File (Passports, Property Papers)
 ├── Kitchen
 │    ├── Upper Cabinet
 │    │    └── Spice Rack
 │    └── Refrigerator
 │         └── Crisper Drawer
 ├── Garage
 │    └── Tool Rack
 │         └── Shelf 2
 └── Master Bedroom
      └── Wardrobe
           └── Top Shelf
```

---

## 3. Location Schema Specification

```sql
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
```

---

## 4. Computed Materialized Path
The system computes the complete hierarchical trail dynamically using recursive CTEs or indexed materialized paths:
$$\text{Home} \longrightarrow \text{Store Room} \longrightarrow \text{3rd Cupboard} \longrightarrow \text{Blue Box}$$

### Recursive CTE Query:
```sql
WITH RECURSIVE location_hierarchy AS (
    SELECT id, home_id, parent_id, name, name AS path, 1 AS depth
    FROM locations
    WHERE parent_id IS NULL AND deleted_at IS NULL
    UNION ALL
    SELECT l.id, l.home_id, l.parent_id, l.name, 
           lh.path || ' > ' || l.name AS path, lh.depth + 1
    FROM locations l
    JOIN location_hierarchy lh ON l.parent_id = lh.id
    WHERE l.deleted_at IS NULL
)
SELECT id, name, path, depth FROM location_hierarchy WHERE home_id = :home_id;
```

---

## 5. Dynamic Customization
No locations are hardcoded. `HOME_ADMIN` and `MEMBER` users can create arbitrary zones, rooms, containers, vehicles, shelves, and safes to match their exact household layout.
