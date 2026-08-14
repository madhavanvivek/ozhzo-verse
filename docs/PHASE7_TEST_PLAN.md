# Ozhzo Verse — Phase 7: MVP Integration Test Plan

## 1. Scope & Verification Strategy
The Phase 7 integration test suite validates that all domestic modules operate together seamlessly as a single Home Operating System while preserving absolute tenant isolation.

---

## 2. Test Vectors Matrix

| # | Test Vector | Description & Assertions | Expected Result |
|---|---|---|---|
| **1** | **Unified Dashboard Pulse** | Query `GET /homes/{id}/dashboard`; returns greeting, attention count, today summary, status KPIs, and recent activity. | HTTP 200 OK |
| **2** | **Attention Ranking** | Create overdue bill, overdue task, low-stock item; assert Attention Center ranks Critical > High > Normal. | HTTP 200 OK with ordered severities |
| **3** | **Unified Today Timeline** | Query `GET /homes/{id}/today`; asserts timeline merges events, tasks due today, bills due today. | HTTP 200 OK with correct source types |
| **4** | **Global Search (Assets)** | Search for `"drill"`; returns exact asset location path and loan status. | HTTP 200 OK with `domain: 'INVENTORY'` |
| **5** | **Global Search (Bills)** | Search for `"electricity"`; returns expected amount, due date, status. | HTTP 200 OK with `domain: 'BILL'` |
| **6** | **Global Search (Tasks)** | Search for `"filter"`; returns due date and assignee. | HTTP 200 OK with `domain: 'TASK'` |
| **7** | **Multi-Home Search Isolation** | User B in Home B searches for Home A's unique asset name; returns 0 results. | 0 results / HTTP 403 on direct access |
| **8** | **Activity Feed Stream** | Perform stock move, task completion, bill payment; query `GET /homes/{id}/activity`; asserts 3 activity entries generated. | HTTP 200 OK with chronological order |
| **9** | **Zero Data Duplication** | Assert no phantom records created in `events`, `tasks`, or `bills` during dashboard or search queries. | Database integrity verified |
| **10** | **Quick Add via Domain Endpoints** | Execute Task, Bill, Event, Purchase Item creation; verify appearance on Dashboard and Today view immediately. | HTTP 201 Created on all actions |
