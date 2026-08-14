# Ozhzo Verse — Unit Master & Home Custom Units Architecture

## 1. Overview & Objectives
Measurement units in Ozhzo Verse support standard global metrics and arbitrary Home-specific custom packaging definitions without hardcoding strings into frontend logic.

```
GLOBAL DEFAULT UNITS (kg, g, L, ml, pcs, pack, box, bottle, can, dozen)
                                ┼
HOME-CUSTOM UNITS (bundle, strip, pouch, packet, roll)
                                │
                                ▼
                   UNIFIED HOME UNITS MASTER
```

---

## 2. Global vs Home-Specific Units
- **Global Units (`home_id IS NULL`)**: System-wide units provided out-of-the-box. Read-only for Home members.
- **Home Custom Units (`home_id = <UUID>`)**: Created by Home Admins / Members (e.g. *bundle* for electrical cords, *strip* for batteries).
- **Soft Deactivation Principle**: Custom units are marked `is_active = FALSE` rather than deleted, safeguarding the referential integrity of past stock movements, purchase records, and inventory history.

---

## 3. Data Model (`units`)
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` (Nullable) | `NULL` = Global default; Non-null = Home custom |
| `name` | `VARCHAR(64)` | Full unit name (e.g. "Kilogram", "Bundle") |
| `symbol` | `VARCHAR(32)` | Display symbol (e.g. "kg", "bundle") |
| `measurement_type` | `VARCHAR(32)` | `WEIGHT`, `VOLUME`, `COUNT`, `LENGTH`, `OTHER` |
| `is_active` | `BOOLEAN` | Active for selection |
| `sort_order` | `INTEGER` | Sorting sequence |

---

## 4. API Endpoints
- `GET /api/v1/homes/{home_id}/units`: List all active units available to this Home.
- `POST /api/v1/homes/{home_id}/units`: Create a Home-custom unit.
- `PATCH /api/v1/homes/{home_id}/units/{id}`: Update or activate custom unit.
- `DELETE /api/v1/homes/{home_id}/units/{id}`: Soft-deactivate custom unit.
