# Ozhzo Verse — Home Inventory Customization & Location Integration

## 1. The Customization Lifecycle
When a Home adds an item from the Global Template catalog or creates a bespoke household item, full customization is immediately supported:

1. **Item Name**: Can be modified (e.g. Global Template *Rice* $\rightarrow$ Home Item *Basmati Rice*).
2. **Unit**: Selected from global or custom units (e.g. *kg*, *packet*, *bundle*).
3. **Thresholds**: Home-specific Minimum Stock (`min_threshold`) and Target Stock (`preferred_quantity`).
4. **Hierarchical Location**: Integrated with the Phase 3A dynamic location tree (`Kitchen > Pantry > 2nd Shelf > Blue Container`).
5. **Completely Independent Custom Items**: Items that do not exist in the global catalog (e.g. *Grandma's Homemade Mango Pickle*) can be created with full feature parity (`template_id = NULL`).

---

## 2. Dynamic Location Path Resolution & Memory
- Physical locations belong exclusively to the Home (`locations` table).
- When items move physically, the move is recorded in `location_movements` without overwriting the previous path audit trail.
- Searching an item (e.g. "Where is the rice?" or "Where is the toolkit?") immediately answers with the full materialized path:
  $$\text{Basmati Rice} \longrightarrow \text{Home } > \text{ Kitchen } > \text{ Pantry } > \text{ 2nd Shelf } > \text{ Blue Container}$$

---

## 3. Purchase List & Restock Integration
- Home Purchase List items optionally link to `inventory_items.id`.
- Marking an item as purchased offers the explicit confirmation prompt: *"Update Home Inventory?"*.
- If accepted, an atomic transaction updates `inventory_items.quantity` and creates an immutable `stock_movements` record of type `PURCHASE`.
