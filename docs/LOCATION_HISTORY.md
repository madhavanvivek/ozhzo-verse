# Ozhzo Verse — Location Movement History

## 1. Overview
Household assets frequently move between rooms, cupboards, and containers. Ozhzo Verse maintains an immutable chronological ledger of all physical asset movements so family members can always trace:
1. *Where is it currently kept?*
2. *Where was it kept previously?*
3. *Who moved it and when?*

---

## 2. Location Movements Schema

```sql
CREATE TABLE IF NOT EXISTS location_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    from_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    to_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    from_location_path TEXT NULL,
    to_location_path TEXT NOT NULL,
    reason TEXT NULL, -- e.g. "Moved for bathroom renovation", "Seasonal storage"
    moved_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    moved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_location_movements_item_time 
ON location_movements (item_id, moved_at DESC);
```

---

## 3. Location Movement Flow & Last Seen Updates

When an item is moved:
1. The previous location path is captured.
2. The new location path is resolved from the location hierarchy.
3. A new `location_movements` record is appended.
4. The `inventory_items` record is updated:
   - `location_id = to_location_id`
   - `last_seen_at = CURRENT_TIMESTAMP`
   - `last_seen_by = moved_by`
   - `last_seen_location_id = to_location_id`
5. An audit log entry `ITEM_MOVED` is written.
