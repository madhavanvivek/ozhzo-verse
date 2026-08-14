# Ozhzo Verse — Phase 3B: Home Purchase List UI/UX Design

## 1. UX Design Philosophy
- **Lightning-Fast Addition**: Adding an essential item to the household list should take under 3 seconds: Enter name, enter quantity, tap **[ Add ]**.
- **Visual Collaboration**: Family members clearly see who requested what item (e.g. *Rice added by Vivek, Milk added by Karthika*).
- **Distraction-Free Shopping**: In-store view provides large checkboxes with instant confirmation.

---

## 2. Key Screen Layouts & User Journeys

### 2.1 Web Purchase List Dashboard
- **Active Purchase List View**:
  - Header: `Madhavan Home — Purchase List (4 Items Pending)`
  - Direct Inline Add Row: `[ Item Name ] [ Qty ] [ Unit ] [ + Add to List ]`
  - Item List Cards / Table:
    - Checkbox: `☐ Milk — 2 L` (Added by Karthika • Full cream)
    - Checkbox: `☐ Basmati Rice — 5 kg` (Added by Vivek • Low Stock Pantry)
    - Checkbox: `☐ Toothpaste — 2 pcs` (Added by Karthika)
    - Checkbox: `☐ Screwdriver — 1 pcs` (Added by Vivek)
- **Low-Stock Suggestion Alert**:
  - Subdued banner when pantry items breach minimum threshold:
    > ⚠️ **Pantry Alert**: *Rice is running low (2 kg left).*  
    > `[ + Add to Purchase List (5 kg) ]` `[ Dismiss ]`
- **Purchase History Tab**:
  - Searchable historical ledger showing dates, items, quantities, and who purchased them.

### 2.2 Mobile Experience (Flutter)
- Large, touch-friendly checkboxes:
  ```
  🛒 PURCHASE LIST
  
  ☐ Milk — 2 L
     Added by Karthika
  
  ☐ Rice — 5 kg
     Added by Vivek
  
  ☐ Toothpaste — 2 pcs
     Added by Karthika
  
  [ + Add Item ]
  ```
- **Checking Off an Item**:
  - Tapping the checkbox marks the item as purchased.
  - If the item is linked to an inventory item, a clean bottom sheet appears:
    > **Update Home Inventory?**  
    > Would you like to add 2 L of Milk to your fridge stock?  
    > `[ Yes, Update Stock ]` `[ No, Just Mark Purchased ]`

---

## 3. User Journeys

```
Journey 1: Quick Manual Addition
Karthika notices milk is finishing ➔ Opens Purchase List ➔ Types "Milk, 2L" ➔ Taps Add ➔ Instantly visible to Vivek.

Journey 2: Low-Stock Inventory Suggestion
Vivek views Home Dashboard ➔ Sees "Sugar is running low" ➔ Taps "+ Add to Purchase List" ➔ Sugar (2 kg) added to list.

Journey 3: Supermarket Shopping & Restock
Vivek is at the grocery store ➔ Opens Purchase List ➔ Taps checkbox on "Milk" ➔ Confirms "Update Inventory" ➔ Milk moves to History and Fridge inventory stock increases to 2L.
```
