# Ozhzo Verse — Home Assets & Unified Inventory Model

## 1. Executive Summary
Ozhzo Verse unifies **Consumable Groceries/Pantry Supplies** and **Durable Household Assets** under a single, cohesive Home Item foundation while maintaining dedicated attributes and behaviors for each item type.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           HOME ITEM FOUNDATION                          │
│                                                                         │
│  ┌──────────────────────────────────┐ ┌──────────────────────────────┐  │
│  │       CONSUMABLES (Pantry)       │ │     ASSETS (Durable Goods)   │  │
│  ├──────────────────────────────────┤ ├──────────────────────────────┤  │
│  │ • Current Quantity               │ │ • Hierarchical Location Path │  │
│  │ • Measurement Unit (kg, L, pcs)  │ │ • Physical Condition         │  │
│  │ • Minimum Threshold (Low Stock)  │ │ • Availability Status        │  │
│  │ • Preferred Restock Target       │ │ • Last Seen (Who, When, Where│  │
│  │ • Expiry Date                    │ │ • Borrow / Lending Status    │  │
│  └──────────────────────────────────┘ └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Item Type Classifications

### Type A: `CONSUMABLE`
- **Definition**: Items that are depleted through regular household usage and require periodic replenishment.
- **Examples**: Rice, Flour, Cooking Oil, Milk, Eggs, Cleaning Detergent, Coffee Beans, Spices, Soap.
- **Key Behaviors**:
  - Quantity tracking and fractional unit measurements.
  - Stock movements ledger (`ADD`, `CONSUME`, `ADJUST`, `WASTE`).
  - Low-stock alerts and automated shopping list integration.

### Type B: `ASSET`
- **Definition**: Reusable physical objects, tools, appliances, files, and equipment permanently owned by the household.
- **Examples**: Toolkit, Cordless Drill, Step Ladder, House Keys, Passport Binder, Vacuum Cleaner, Camping Tent, Extension Cords.
- **Key Behaviors**:
  - Exact hierarchical location storage (`Home > Garage > Tool Rack > Shelf 2`).
  - Physical condition tracking (`NEW`, `EXCELLENT`, `GOOD`, `FAIR`, `POOR`, `DAMAGED`).
  - Availability status (`AVAILABLE`, `BORROWED`, `MISSING`, `ARCHIVED`).
  - Last Seen memory (`Last seen by Vivek on 12 Aug 2026 at Store > Blue Box`).
  - Temporary lending & return ledger (`asset_loans`).

---

## 3. Unified Entity Attributes

| Attribute | Consumables | Assets | Description |
|---|:---:|:---:|---|
| `id` | Yes | Yes | Unique UUID identifier |
| `home_id` | Yes | Yes | Owning Home tenant boundary |
| `item_type` | `CONSUMABLE` | `ASSET` | Type discriminator |
| `category_id` | Yes | Yes | Category grouping |
| `name` | Yes | Yes | Name of item / asset |
| `description` | Yes | Yes | Detailed description / specs |
| `location_id` | Optional | **Primary** | Current location in hierarchy |
| `quantity` & `unit` | **Primary** | Optional (default 1 pcs) | Quantitative on-hand count |
| `min_threshold` | **Primary** | N/A | Low stock alert threshold |
| `preferred_quantity` | **Primary** | N/A | Restock target level |
| `condition` | N/A | **Primary** | Physical state of asset |
| `asset_status` | Derived | **Primary** | `AVAILABLE`, `BORROWED`, `MISSING`, `ARCHIVED` |
| `last_seen_at` | N/A | **Primary** | Timestamp of last physical verification |
| `last_seen_by` | N/A | **Primary** | Member who last verified asset location |
| `notes` | Yes | Yes | General remarks |
| `created_by` | Yes | Yes | Audit creator |
