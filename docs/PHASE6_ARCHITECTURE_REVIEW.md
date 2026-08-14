# Ozhzo Verse — Phase 6: Architecture Review & 20 Clarifications

**Document**: Phase 6 Shared Calendar & Household Events Architecture Review  
**Status**: PLANNING GATE REVIEW  
**Scope**: 20 Architectural Questions & Implementation Answers  

---

### 1. What is a household Event?
A household Event represents a point-in-time or duration-based family occurrence (e.g. Birthday, Anniversary, School Parent Meeting, Doctor Appointment, Holiday, Trip, Maintenance Visit, Visitor Arrival) belonging to a specific Home.

### 2. How is an Event different from a Task?
- An **Event** answers *"What is happening and when?"* It happens at a specific time or date (e.g. Doctor appointment at 10:00 AM) and does not have an actionable "completion" state like a chore.
- A **Task** answers *"What needs to be done?"* (e.g. "Clean water filter"). It is an actionable work item with a state machine (`TODO` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `COMPLETED`).

### 3. How is an Event different from a Bill?
- An **Event** is a temporal gathering, appointment, or routine.
- A **Bill** is a household financial liability with expected amounts, payment transactions, remaining balances, and financial ledgers.

### 4. How is the Calendar Projection designed?
The Calendar Projection is a read-only dynamic aggregation service (`GET /homes/{home_id}/calendar/projection`). When queried for a date range, it simultaneously queries `events`, `tasks`, and `bills`, merges the results in chronological order, and maps them to a unified `TimelineItemDTO` discriminated by `item_type: 'EVENT' | 'TASK' | 'BILL'`. Zero data is duplicated across database tables.

### 5. How are recurring events represented?
Recurring events use the standard Ozhzo recurrence fields (`recurrence_type`: `NONE`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `CUSTOM_DAYS`, and `parent_recurring_event_id`).

### 6. How are event occurrences generated?
Occurrences are generated using the `SCHEDULED_DATE` calendar recurrence strategy, advancing fixed intervals (e.g. every year on August 15 for a birthday, or every Sunday for a family call).

### 7. How are duplicate occurrences prevented?
Database composite checks against `(home_id, parent_recurring_event_id, start_time)` and atomic transaction blocks prevent simultaneous duplicate occurrence generation.

### 8. How are timezones handled?
All timestamps are stored in UTC (`TIMESTAMPTZ`). The Home's configured timezone (`homes.timezone`) provides the authoritative anchor for all-day event boundaries (00:00:00 to 23:59:59) and calendar month/week grid grouping.

### 9. How are all-day events handled?
All-day events have `is_all_day = true`. The API accepts date strings (e.g. `2026-08-15`) and expands them to full local days in the Home's timezone without requiring arbitrary hour timestamps.

### 10. How are participants handled?
Participants are linked via the `event_participants` table (`event_id`, `user_id`, `status`). The backend strictly validates that every participant is an `ACTIVE` member of the owning Home.

### 11. How is multi-home isolation enforced?
Every calendar query and mutation asserts `home_id == home_ctx.home_id` backed by `require_home_permission(...)` middleware. Cross-home access is blocked with `403 Forbidden`.

### 12. How is RBAC enforced?
- `calendar:view`: Granted to all active home members (`OWNER`, `ADMIN`, `MEMBER`, `GUEST`).
- `calendar:create`, `calendar:edit`: Granted to `OWNER`, `ADMIN`, `MEMBER`.
- `calendar:delete`: Granted to `OWNER`, `ADMIN`.

### 13. How are cancelled events preserved?
When an event is deleted or cancelled, it is soft-deleted by setting `deleted_at = NOW()` and `status = 'CANCELLED'`. Historical records remain in the database for audit integrity.

### 14. How are reminders represented?
Events store `reminder_minutes_before` (e.g. 30, 60, 1440 for 1 day before). Notification engine evaluates upcoming events against user notification preferences.

### 15. How can Bills appear in Calendar?
Through the Calendar Projection endpoint: bills with `due_date` falling inside the queried window are dynamically included as `item_type: 'BILL'` with amount, status, and responsible member metadata.

### 16. How can Tasks appear in Calendar?
Through the Calendar Projection endpoint: tasks with `due_date` falling inside the window are dynamically included as `item_type: 'TASK'` with priority, status, and assignee metadata.

### 17. How can Asset dates appear in Calendar?
Asset warranty expiry or service dates can be projected via Task or Projection queries without creating duplicate calendar event rows.

### 18. How can Inventory expiry appear in Calendar?
Inventory batches with expiration dates can be projected on the timeline without mutating the inventory tables.

### 19. What is explicitly OUT OF SCOPE?
- External Google/Outlook/Apple CalDAV two-way sync.
- Zoom / Google Meet automated video room generation.
- Enterprise free/busy meeting room resource scheduling.
- GPS navigation and mapping integrations.

### 20. How does Phase 6 remain simple and household-focused?
By focusing strictly on family schedule coordination (birthdays, school events, doctor visits, trips, visitor arrivals) and providing a unified temporal lens over existing Tasks and Bills without data duplication.
