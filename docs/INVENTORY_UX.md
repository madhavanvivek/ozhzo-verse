# Ozhzo Verse — Phase 3A: Inventory & Asset UI/UX Design

## 1. Unified Dashboard Architecture
The Dashboard is split into two complementary perspectives with a central search experience:
1. **Pantry & Consumables**: Focuses on stock levels, low-stock alerts, units, and quick consume buttons.
2. **Household Assets & Tools**: Focuses on physical locations (`Where is it?`), current custody (`Who has it?`), and loan statuses.

---

## 2. Key Screen & Interaction Designs

### 2.1 Universal Item & Location Search
- Instant debounced multi-facet search:
  - Querying `"Toolkit"` $\rightarrow$ Shows item card with location badge `📍 Store > 3rd Cupboard > Blue Box`.
  - Querying `"Blue Box"` $\rightarrow$ Shows location card listing all contained items (`Toolkit`, `Screwdrivers`, `Tape`).
  - Querying `"Borrowed"` $\rightarrow$ Filters to all currently loaned assets with borrower names and return due dates.

### 2.2 Hierarchical Location Explorer (Web & Mobile)
- Cascading tree view / folder view:
  ```
  🏠 Home
   ├── 🚪 Entrance (2 items)
   ├── 📦 Store Room
   │    └── 🗄️ 3rd Cupboard
   │         └── 🟦 Blue Box (3 assets)
   └── 🍳 Kitchen (34 items)
  ```
- Clicking any location displays the contained items with immediate action controls.

### 2.3 Quick Item Actions
- **`[ Move ]` Action**:
  - Opens a lightweight location selector modal/sheet.
  - User taps the destination location (e.g. `Garage > Tool Rack > Shelf 2`).
  - Instantly logs a location movement and updates `Last Seen`.
- **`[ Borrow ]` Action**:
  - Prompts for Borrower Name (or selection from Home members), optional contact info, expected return date, and notes.
  - Turns status badge from 🟢 `AVAILABLE` to 🟡 `BORROWED (Ashraf)`.
- **`[ Return ]` Action**:
  - Prompts: *"Where was it placed upon return?"* (pre-selects last known location).
  - Tapping Confirm logs return timestamp and sets asset back to `AVAILABLE`.
