# Ozhzo Verse — Phase 7: Global Search & Home Memory Architecture

## 1. Vision & Household Memory Concept
A primary superpower of Ozhzo Verse is **Home Memory**: answering the perennial domestic frustration:
**"WHERE IS IT? WHO HAS IT? WHEN WAS IT LAST SEEN?"**

Global Search is a multi-domain, deterministic query engine that scans across all household assets, consumables, physical locations, shopping items, chores, bills, and family events in milliseconds.

---

## 2. Searchable Domain Matrix & Ranking Rules

| Domain | Search Fields | Highlighting & Location Path Display | Rank Weight |
|---|---|---|---|
| **Durable Assets** | `name`, `description`, `location_path`, `current_holder_name`, `condition` | Displays exact hierarchical location (e.g. `Home ➔ Garage ➔ Tool Cabinet ➔ Shelf 2`) and status (`AVAILABLE` or `BORROWED by Vivek`). | 1.0 (Top) |
| **Inventory Consumables** | `name`, `description`, `location_path`, `notes` | Displays stock level (`3 kg`), unit, and location (e.g. `Kitchen ➔ Pantry ➔ 2nd Shelf`). | 0.9 |
| **Physical Locations** | `name`, `description`, `location_type` | Displays location path and number of stored items. | 0.8 |
| **Tasks & Chores** | `title`, `description`, `notes` | Displays due date, priority, and assigned member. | 0.7 |
| **Bills & Obligations** | `title`, `notes` | Displays expected amount, currency, due date, and payment status (`UNPAID` / `PAID`). | 0.7 |
| **Calendar Events** | `title`, `description`, `location` | Displays event start/end, all-day status, and location. | 0.6 |
| **Purchase Items** | `name`, `notes` | Displays quantity needed and shopping status. | 0.5 |
| **Home Members** | `first_name`, `last_name`, `email` | Displays member role and display name. | 0.5 |

---

## 3. Query Architecture & Performance Optimization

```sql
-- Conceptual Unified Search Query Structure (Executed within a single database transaction)
-- Strict Home Scoping Invariant: Every subquery asserts home_id = :current_home_id

-- 1. Search Assets & Inventory
SELECT id, 'INVENTORY' AS domain, name AS title, 
       COALESCE(location_path, 'Unassigned') AS location_summary,
       status, asset_status, current_holder_name, 1.0 AS relevance
FROM inventory_items 
WHERE home_id = :home_id AND deleted_at IS NULL 
  AND (name ILIKE :term OR location_path ILIKE :term OR description ILIKE :term)

UNION ALL

-- 2. Search Tasks
SELECT id, 'TASK' AS domain, title, 
       TO_CHAR(due_date, 'YYYY-MM-DD') AS location_summary,
       status, NULL, NULL, 0.7 AS relevance
FROM tasks 
WHERE home_id = :home_id AND deleted_at IS NULL 
  AND (title ILIKE :term OR description ILIKE :term)

UNION ALL

-- 3. Search Bills
SELECT id, 'BILL' AS domain, title, 
       CONCAT(currency, ' ', expected_amount) AS location_summary,
       status, NULL, NULL, 0.7 AS relevance
FROM bills 
WHERE home_id = :home_id AND deleted_at IS NULL 
  AND (title ILIKE :term OR notes ILIKE :term)

UNION ALL

-- 4. Search Calendar Events
SELECT id, 'EVENT' AS domain, title, 
       COALESCE(location, 'Home') AS location_summary,
       status, NULL, NULL, 0.6 AS relevance
FROM events 
WHERE home_id = :home_id AND deleted_at IS NULL 
  AND (title ILIKE :term OR location ILIKE :term)

ORDER BY relevance DESC, title ASC 
LIMIT :limit;
```

---

## 4. API Endpoint Specification

### `GET /api/v1/homes/{home_id}/search`
- **Auth**: Bearer Token (`homes:view`)
- **Query Params**:
  - `q`: Search query string (min 1, max 100 chars, e.g. `toolkit`, `drill`, `electricity`).
  - `domain`: Optional filter (`INVENTORY`, `ASSET`, `LOCATION`, `TASK`, `BILL`, `EVENT`, `PURCHASE`, `MEMBER`).
  - `limit`: int (default 20, max 50).
- **Security Guarantee**: Multi-home isolation is absolute; cross-home data leakage is physically impossible.
