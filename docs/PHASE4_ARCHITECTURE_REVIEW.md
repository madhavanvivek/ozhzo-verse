# Ozhzo Verse — Phase 4 Architecture Review: Tasks & Household Responsibilities

This document provides explicit architectural answers for the Phase 4 Planning Gate.

---

## 1. What is a Task?
In Ozhzo Verse, a **Task** represents an action, chore, or maintenance responsibility required to maintain the physical, financial, or operational wellbeing of the Home.
- Examples: *Clean water filter*, *Service AC*, *Pay electricity bill*, *Change gas cylinder*, *Take dog to vet*, *Water garden*.
- It is strictly **household-focused**, omitting corporate ticketing overhead.

---

## 2. What belongs to the Home?
**The Task and its full lifecycle belong to the Home.**
- The Home is the primary tenant (`home_id`).
- All active household members share visibility into Home Tasks.
- The task does not disappear or become private if the creator leaves or reassigns it.

---

## 3. What belongs to the Member?
- **Task Authorship Audit**: `created_by` (logs which family member created the task).
- **Execution Responsibility**: `assigned_to` (the member assigned to perform the chore).
- **Completion Audit**: `completed_by` and `completed_at` (logs which member completed it).
- **"My Tasks" View**: A convenience view filtering Home tasks where `assigned_to = current_user.id`.

---

## 4. How does assignment work?
- Assignment is **completely optional**.
- An unassigned task is displayed on the general Home Board for any family member to pick up.
- Any authorized member can assign a task to themselves or another verified Home member.
- Tasks can be unassigned at any time (`assigned_to = NULL`), returning to the shared pool.

---

## 5. How does recurrence work?
- A task can define:
  - `recurrence_type`: `NONE`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `CUSTOM_DAYS`.
  - `recurrence_interval_days`: e.g. 14, 30, 180.
  - `recurrence_strategy`:
    1. **`SCHEDULED_DATE` (Fixed Calendar Schedule)**: Next occurrence is calculated from the scheduled `due_date` (e.g. monthly rent due on 1st of every month).
    2. **`COMPLETION_DATE` (Physical Maintenance Rhythm)**: Next occurrence is calculated from the actual `completed_at` timestamp (e.g. clean water filter 30 days after it was actually cleaned).

---

## 6. How is task history preserved?
- Completing a task sets `status = 'COMPLETED'`, `completed_by = current_user.id`, and `completed_at = NOW()`.
- Completed tasks are never overwritten or deleted.
- They remain in the permanent, searchable **Task Completion History**, providing an audit trail for appliance maintenance, vehicle service, and household chore routines.

---

## 7. How are overdue tasks derived?
- Overdue is a **dynamically derived calculation**, not a static database status string:
  $$\text{is\_overdue} = (\text{due\_date} < \text{current\_time}) \land (\text{status} \neq \text{'COMPLETED'}) \land (\text{status} \neq \text{'CANCELLED'})$$
- This guarantees real-time accuracy without requiring periodic background status-mutating cron jobs.

---

## 8. How are recurring occurrences prevented from duplicating?
- **Atomic Database Transaction**: Marking a task completed and spawning the next occurrence are executed within the same atomic transaction.
- **Optimistic Concurrency Locking**: Integer `version` column ensures that if two family members tap complete simultaneously, only the first transaction succeeds; the second receives HTTP 400 Bad Request.
- **Root Pointer**: Each spawned occurrence links back to `parent_recurring_task_id`.

---

## 9. How does Multi-Home isolation work?
- Every task query and mutation enforces `home_id = home_ctx.home_id`.
- If a user belongs to Home A and Home B:
  - Home A's tasks are completely invisible while operating in Home B context.
  - Attempting to pass Home A's `task_id` in a Home B request returns `403 Forbidden` / `404 Not Found`.

---

## 10. How does RBAC work?
- Reuses existing Ozhzo Home RBAC:
  - `tasks:view`: `HOME_ADMIN`, `MEMBER`, `CHILD`, `GUEST`.
  - `tasks:create`: `HOME_ADMIN`, `MEMBER`, `CHILD`.
  - `tasks:edit`, `tasks:complete`: `HOME_ADMIN`, `MEMBER`, `CHILD`.
  - `tasks:delete`: `HOME_ADMIN`, `MEMBER`.
- Unverified mobile accounts cannot mutate task data.

---

## 11. How can Tasks integrate with Inventory / Purchase / Assets later?
- Clean architectural boundaries are preserved:
  - **Asset Maintenance**: Future tasks can link to `asset_id` (*"Service Generator" $\rightarrow$ Generator in Utility Room*).
  - **Purchase List Trigger**: Completing a maintenance task (*"Change water filter"*) can suggest adding replacement filters to the Purchase List.
  - **Inventory Restock Trigger**: Low stock alerts can suggest a task (*"Buy Cooking Oil"*).
- None of these integrations are tightly coupled in Phase 4, keeping the task engine fast and lightweight.
