# Ozhzo Verse — Phase 6: Shared Calendar & Household Events Test Plan

## 1. Scope & Verification Strategy
The Phase 6 test suite validates the Shared Calendar and unified temporal projection engine across 22 functional, security, concurrency, and multi-tenant test vectors.

---

## 2. Test Vectors Matrix

| # | Test Vector | Description & Assertion Criteria | Expected Result |
|---|---|---|---|
| **1** | **Quick Event Creation** | Create event with `title`, `start_time`, `end_time`. | HTTP 201 Created |
| **2** | **All-Day Event** | Create event with `is_all_day = true` spanning 00:00 to 23:59. | HTTP 201 Created |
| **3** | **Multi-Day Event** | Create trip event spanning multiple calendar dates. | HTTP 201 Created |
| **4** | **End Before Start Rejection** | Submit `end_time < start_time`. | HTTP 422 Unprocessable Entity |
| **5** | **Participant Assignment** | Add active Home members as participants. | HTTP 201 Created with `INVITED` |
| **6** | **Cross-Home Participant Rejection** | Assign user who is not a member of the Home. | HTTP 400 Bad Request |
| **7** | **Participant Status Update** | Participant updates own status to `ACCEPTED` or `DECLINED`. | HTTP 200 OK |
| **8** | **Event Update with Concurrency** | Update title/location with matching `version`. | HTTP 200 OK, `version + 1` |
| **9** | **Optimistic Lock Conflict** | Update with mismatched `version`. | HTTP 409 Conflict |
| **10** | **Soft-Delete / Cancellation** | Delete event; assert `deleted_at` is set and status is `CANCELLED`. | HTTP 200 OK |
| **11** | **Query Range Filter** | Query events within `start_date` and `end_date`. | HTTP 200 OK with filtered list |
| **12** | **Category CRUD** | Create and list home-scoped event categories. | HTTP 201 / HTTP 200 |
| **13** | **Recurring Annual Birthday** | Recurring `YEARLY` event schedule. | HTTP 201 Created |
| **14** | **Recurring Weekly Meeting** | Recurring `WEEKLY` event schedule. | HTTP 201 Created |
| **15** | **Calendar Projection (Events)** | Query projection endpoint; returns active calendar events. | HTTP 200 with `item_type: 'EVENT'` |
| **16** | **Calendar Projection (Tasks)** | Query projection endpoint; returns due tasks in window. | HTTP 200 with `item_type: 'TASK'` |
| **17** | **Calendar Projection (Bills)** | Query projection endpoint; returns due bills in window. | HTTP 200 with `item_type: 'BILL'` |
| **18** | **Projection Zero-Duplication** | Assert no task or bill records were created in `events` table. | Database integrity verified |
| **19** | **Multi-Home Isolation** | User B in Home B cannot access Home A events. | HTTP 403 Forbidden |
| **20** | **Client-Side Home ID Tampering** | Server rejects client-injected foreign home IDs in payload. | HTTP 403 Forbidden |
| **21** | **Timezone Correctness** | Query with UTC timestamps matching Home timezone. | Timestamps preserved |
| **22** | **Historical Preservation** | Past events remain queryable in range queries. | Historical events visible |
