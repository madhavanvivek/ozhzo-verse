# Ozhzo Verse — Phase 3B: Shopping UI/UX Design

## 1. UX Design Philosophy
- **Frictionless In-Store Shopping Mode**: Optimized for one-handed operation while navigating supermarket aisles with large tap targets and zero unnecessary navigation.
- **Clear Household Replenishment Funnel**: Surfaces low-stock inventory items as actionable suggestions without cluttering the active cart.

---

## 2. Key Screen Layouts & User Journeys

### 2.1 Household Shopping Board (Desktop & Mobile)
- **Top Metrics Bar**:
  - `Items to Buy` (e.g. 12 Items)
  - `High Priority` (e.g. 3 Items)
  - `Low Stock Suggestions` (e.g. 4 Items)
  - `In Cart` (e.g. 2 Items)
- **Smart Suggestions Tray**:
  - Expandable banner: *"4 items running low in your pantry. Review & add to shopping list."*
  - 1-tap `[ + Add to List ]` on each suggested item with pre-calculated restock quantities (`Basmati Rice — Buy 8 kg`).
- **Interactive List View**:
  - Filter pills: `All`, `High Priority`, `Assigned to Me`, `By Category`.
  - Item cards with priority indicators (🔴 High, 🟡 Normal, ⚪ Low), buyer avatar badges, and quick quantity steppers.

### 2.2 Mobile-First "Shopping Mode"
- Fullscreen mode designed for supermarket navigation.
- Big checkbox items:
  ```
  [  ] Basmati Rice — 8 kg (Pantry)
  [  ] Organic Whole Milk — 2 L (Fridge)
  [  ] Extra Virgin Olive Oil — 1 L (Pantry)
  ```
- Tapping an item opens the **Quick Checkout Drawer**:
  - `[ Mark Purchased ]`
  - Toggle: *"Add to Home Inventory?"* (Default: Checked for inventory-linked items).
  - Optional store name / actual price input.
  - Tapping Confirm restocks inventory and moves item to Completed History.

### 2.3 User Journeys

```
Journey 1: Manual Addition
Member taps "+ Add Item" ➔ Enters "Almond Milk, 2L, High Priority" ➔ Shared with all members.

Journey 2: Low-Stock Replenishment
Pantry Rice drops to 2kg (Min: 5kg, Preferred: 10kg) ➔ Suggestion appears: "Rice: Buy 8kg" ➔ Member taps "+ Add".

Journey 3: Supermarket Shopping & Restock
Shopper enables "Shopping Mode" ➔ Checks "Rice 8kg" ➔ Confirms "Restock Inventory" ➔ Inventory increases from 2kg to 10kg.

Journey 4: Task Delegation
Member assigns "Car Engine Oil" to "Vivek" ➔ Vivek receives notification badge on his mobile shopping tab.
```
