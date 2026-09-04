# OZHZO VERSE — PRODUCTION SMOKE TEST SPECIFICATION

---

## 1. Overview & Non-Destructive Principles

The production smoke test verifies end-to-end platform health after any production deployment without corrupting, overwriting, or deleting real household data.

---

## 2. 14-Point Verification Checklist

1. **Health Endpoint**: `GET /health` and `GET /health/readiness` return HTTP 200 with all dependencies green.
2. **Authentication**: Authenticate user via JWT session and verify token integrity.
3. **Home Access & Context**: Resolve user active workspace and load membership permissions.
4. **Dashboard Aggregation**: Query unified household dashboard overview (tasks, bills, alerts).
5. **Tasks Module**: Query task listing and verify filter boundaries.
6. **Shopping Module**: Query active purchase items and inventory link.
7. **Calendar Module**: Query unified timeline aggregation across events, chores, and bills.
8. **Inventory Module**: Query tracked household items and stock indicators.
9. **Notification Center**: Query active priority alerts and notification center feed.
10. **AI Assistant (Read)**: Execute safe contextual query ("What's due today?").
11. **Automations (Read)**: Query active automation rules and execution audit history.
12. **Subscription & Entitlements**: Verify household tier, quota limits, and renewal dates.
13. **Global Multi-Domain Search**: Query Cmd+K search endpoint for household records.
14. **Logout & Session Boundary**: Clear session and verify unauthenticated rejection (HTTP 401).
