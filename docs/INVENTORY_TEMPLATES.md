# Ozhzo Verse — Global Inventory Templates Architecture

## 1. Product Objective & Principle
Ozhzo provides Homes with a ready-to-use catalog of common household inventory items so family members do not have to configure standard groceries, pantry staples, and supplies from scratch.

$$\text{Global Inventory Template Catalog} \longrightarrow \text{Home Selects Item} \longrightarrow \text{Home Customizes} \longrightarrow \text{Home-Owned Inventory Item}$$

---

## 2. Non-Negotiable Boundary: Template vs. Home Item
1. **Global Templates are NOT actual inventory**: A Global Template represents catalog metadata only (e.g. *Rice, Default Category: Pantry, Default Unit: kg*).
2. **Strict Copy-on-Write**: When a Home adds an item from a template, a brand new record is created in `inventory_items` belonging exclusively to that `home_id`.
3. **Immutability of Existing Home Data**: If Super Admin alters a global template (e.g. changing Rice's default unit from `kg` to `packet`), existing Home inventory items remain **100% unaffected**.

---

## 3. Data Model (`inventory_templates`)
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `name` | `VARCHAR(120)` | Template name (e.g. "Rice", "Sugar", "Milk") |
| `default_category_name` | `VARCHAR(100)` | Suggested category name (e.g. "Pantry", "Refrigerator") |
| `default_unit` | `VARCHAR(32)` | Suggested default unit (e.g. "kg", "L", "pcs") |
| `description` | `TEXT` | Brief household description |
| `is_active` | `BOOLEAN` | Active for catalog selection |
| `sort_order` | `INTEGER` | Display order in catalog |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | Timestamps |

---

## 4. API Endpoints
- `GET /api/v1/inventory/templates`: Available to all authenticated users for the "Common Items" catalog selector.
- `POST /api/v1/admin/inventory/templates`: Super Admin creates new global template.
- `PATCH /api/v1/admin/inventory/templates/{id}`: Super Admin updates global template.
- `DELETE /api/v1/admin/inventory/templates/{id}`: Super Admin deactivates global template.
