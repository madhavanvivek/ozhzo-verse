# Ozhzo Verse — Phase 7: Product Analytics & Telemetry Framework

## 1. Analytics Principles
- **Privacy-Preserving**: No plain-text passwords, personal notes, or monetary account details logged.
- **Home-Scoped & Action-Oriented**: Telemetry measures user activation, retention, and feature engagement.

---

## 2. Standardized MVP Event Taxonomy

| Event Name | Trigger Condition | Properties Captured |
|---|---|---|
| `dashboard_opened` | User navigates to Home Dashboard | `home_id`, `active_attention_count`, `today_items_count` |
| `today_view_opened` | User opens Today view | `home_id`, `filter_type` |
| `quick_add_used` | User triggers creation from Global Quick Add | `home_id`, `entity_type` (`task`, `bill`, `event`, `purchase`, `inventory`) |
| `search_performed` | User executes a search in Home Memory | `home_id`, `query_length`, `results_count`, `domain_filter` |
| `search_result_opened` | User taps/clicks a search result | `home_id`, `target_domain`, `result_rank` |
| `task_completed` | User marks a task done | `home_id`, `task_id`, `is_recurring` |
| `bill_paid` | User records full/partial bill payment | `home_id`, `bill_id`, `payment_method`, `is_partial` |
| `purchase_checked` | User checks off item from Purchase List | `home_id`, `item_id`, `auto_restocked` (bool) |
| `asset_loan_created` | User records an asset loan | `home_id`, `asset_id`, `has_return_date` |
