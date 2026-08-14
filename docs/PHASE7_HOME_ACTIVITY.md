# Ozhzo Verse — Phase 7: Home Activity Feed Architecture

## 1. Concept & Domestic Collaboration
The **Home Activity Feed** gives family members shared visibility into recent actions taken in the household. It fosters coordination without requiring manual status texts.

---

## 2. Activity Event Sources & Data Aggregation

Rather than maintaining a heavy duplicate event bus, the Activity Feed is dynamically aggregated from existing immutable transaction tables:

| Event Type | Source Table | Description Template | Navigation Target |
|---|---|---|---|
| **Stock Movement** | `stock_movements` | `{user} {movement_type} {quantity} {unit} of {item_name}` | `/inventory/{item_id}` |
| **Location Movement** | `location_movements` | `{user} moved {item_name} from {old_loc} to {new_loc}` | `/inventory/{item_id}` |
| **Task Completed** | `tasks` (`status = 'COMPLETED'`) | `{user} completed task "{task_title}"` | `/tasks/{task_id}` |
| **Bill Paid** | `bill_payments` | `{user} recorded payment of {currency} {amount} for "{bill_title}"` | `/bills/{bill_id}` |
| **Purchase Checked** | `purchase_items` (`is_checked = TRUE`) | `{user} purchased {quantity} {unit} of {item_name}` | `/purchase-list` |
| **Asset Loaned** | `asset_loans` | `{user} borrowed {asset_name} (Expected return: {date})` | `/inventory/assets/{asset_id}` |

---

## 3. API Endpoint Specification

### `GET /api/v1/homes/{home_id}/activity`
- **Auth**: Bearer Token (`homes:view`)
- **Query Params**:
  - `limit`: int (default 15, max 50).
  - `offset`: int (default 0).
- **Response**: Chronologically sorted list of human-readable activity events with relative timestamps (e.g. *"10 minutes ago"*).
