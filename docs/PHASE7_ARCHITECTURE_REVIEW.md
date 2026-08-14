# Ozhzo Verse — Phase 7: Architecture Review & 20 Clarifications

**Document**: Phase 7 Architecture Review  
**Status**: PLANNING GATE REVIEW  
**Scope**: 20 Architectural Questions & Implementation Answers  

---

### 1. What belongs on the Home Dashboard?
The Home Dashboard provides an immediate operational pulse:
1. **Greeting & Date Pulse**: Home name, personalized greeting, time of day.
2. **Attention Banner**: Ranked urgent items (overdue bills, overdue chores, empty pantry stock).
3. **Today at a Glance**: Chronological timeline of today's events, tasks, and bills.
4. **Global Quick Add**: Fast-entry buttons (+ Task, + Shopping Item, + Inventory, + Asset, + Bill, + Event).
5. **Home Health KPIs**: Active tasks, low-stock count, unpaid bill sum, borrowed assets count.
6. **Recent Activity Feed**: Latest 5 household actions across family members.

### 2. What belongs in Today?
Everything scheduled, due, or requiring action on the current calendar date:
- Events spanning or starting today (`source_type: EVENT`).
- Tasks with `due_date = today` and `status != 'COMPLETED'` (`source_type: TASK`).
- Bills with `due_date = today` and `status IN ('UNPAID', 'PARTIALLY_PAID')` (`source_type: BILL`).
- High-priority / urgent items on the Purchase List (`source_type: PURCHASE`).
- Pantry consumables that are completely out of stock (`source_type: INVENTORY`).

### 3. How does Global Search work?
Global Search is a multi-domain, deterministic search engine querying `inventory_items` (consumables & durable assets), `locations`, `tasks`, `bills`, `events`, `purchase_items`, and `home_members` in a single server-side operation. Results return ranked items with location breadcrumbs, statuses, and direct deep links.

### 4. How do we search Home Memory?
Home Memory searches the physical whereabouts of items and assets (e.g. searching "drill" returns *"Bosch Electric Drill — Garage ➔ Tool Cabinet ➔ Shelf 2 — Status: BORROWED by Vivek"*).

### 5. How do we prevent cross-home search leakage?
Every search query strictly appends `WHERE home_id = :home_ctx.home_id` and is guarded by `require_home_permission(...)` middleware. Cross-home data matching is physically impossible.

### 6. How does Quick Add interact with existing APIs?
Quick Add does not create duplicate entities; it acts as a lightweight client-side dispatcher calling the established domain endpoints (`POST /tasks`, `POST /purchase-list/items`, `POST /inventory/items`, `POST /bills`, `POST /events`).

### 7. How should Attention be prioritized?
By four distinct severity tiers:
- **CRITICAL (Red)**: Overdue Bills, Overdue Tasks.
- **HIGH (Amber)**: Bills Due Today, Tasks Due Today, Out of Stock Supplies.
- **NORMAL (Yellow)**: Low Stock Supplies, Overdue Asset Returns.
- **INFO (Blue)**: Events happening today, pending invitations.

### 8. How should Activity be generated?
By dynamically querying immutable transaction tables (`stock_movements`, `location_movements`, `tasks` completion, `bill_payments`, `asset_loans`) and rendering them in chronological order without creating separate duplicate activity logs.

### 9. What should the first-time user see?
A warm, progressive starter screen:
1. Workspace Name & Currency Confirmation.
2. Optional Member Invitations.
3. One-Click Template Starter Pack (pick common bills like Electricity and common chores like Clean AC Filter).
4. Direct arrival at an organized Home Dashboard.

### 10. How does the Home Switcher work?
A dropdown in the top header displaying all Homes the user belongs to. Selecting a new Home immediately updates client context, clears stale cache, and re-fetches all dashboard and search views scoped to the new `home_id`.

### 11. What belongs in bottom navigation on Mobile?
5 clean, thumb-friendly tabs:
1. 🏠 **Home** (Dashboard Pulse & Attention)
2. 📅 **Today** (Daily Agenda & Schedule)
3. ➕ **Add** (Universal Quick Add FAB)
4. 📦 **Memory** (Inventory & Assets Search)
5. ☰ **More** (Tasks, Purchase List, Bills, Settings)

### 12. What belongs in Web navigation?
- **Top Header**: Home Switcher, Global Search bar (`Cmd+K`), Quick Add button (`+ Add`), Notification Bell, User Profile.
- **Sidebar**: Dashboard, Today & Calendar, Home Memory (Inventory & Assets), Purchase List, Tasks & Chores, Bills & Expenses, Home Settings.

### 13. How do Tasks and Bills appear without duplication?
Through dynamic **Temporal Projections**. The Today and Calendar endpoints query `tasks` and `bills` in real time, projecting them as `TimelineItemDTO` with `source_type: 'TASK'` / `'BILL'` and direct navigation targets, without copying records into the `events` table.

### 14. How does Inventory connect to Shopping?
When an inventory item drops to or below `min_threshold`, it triggers a `LOW_STOCK` status, surfaces in the Attention Center, and provides a one-click button: `[+ Add to Purchase List]`. Checking an item off the purchase list can automatically restock the linked inventory item.

### 15. How does Asset Location connect to Search?
Durable assets in `inventory_items` maintain a denormalized `location_path` (e.g. `Home ➔ Store Room ➔ Cupboard 3`). When searched, the location breadcrumb and lending status are immediately returned.

### 16. What is the minimum MVP experience?
A unified home where family members can:
- See what needs attention today.
- Find where any tool or item is stored.
- Add an item to the shopping list or chores in 2 seconds.
- Track who owes what for upcoming bills.

### 17. What should explicitly NOT be implemented?
- AI chatbot assistants.
- Social feeds or public sharing.
- External banking / payment gateway APIs.
- External CalDAV / Google sync.
- IoT device automation protocols.

### 18. How do we preserve future AI compatibility?
By maintaining clean, strictly typed, relational domain models with clear temporal and spatial breadcrumbs (`location_path`, `due_date`, `status`, `assigned_to`). Future LLM agents can query these clean structured endpoints directly.

### 19. How do we measure MVP usage?
Through privacy-preserving telemetry tracking: `dashboard_opened`, `today_view_opened`, `quick_add_used`, `search_performed`, `task_completed`, `bill_paid`, and `search_result_opened`.

### 20. What are the major performance risks?
N+1 query cascades on dashboard and search queries. **Mitigation**: Use SQL `UNION ALL` or `asyncio.gather` parallel queries with indexed lookups on `(home_id, deleted_at)` and in-memory Redis caching for dashboard pulses.
