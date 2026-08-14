# Ozhzo Verse — Phase 4: Tasks & Household Responsibilities Test Plan

## 1. Scope & Strategy
This test plan provides comprehensive automated coverage for the Home Tasks engine, quick additions, member assignment, recurring schedule calculations, completion history, optimistic concurrency, and multi-home security isolation.

---

## 2. Test Suite Matrix

### 2.1 Task CRUD & Assignment
1. **Quick Task Creation**: Create task with minimal payload (`title` only). Verify defaults: `priority = 'NORMAL'`, `status = 'TODO'`, `due_date = NULL`.
2. **Detailed Task Creation**: Create task with description, priority (`HIGH`), due date, and assigned member.
3. **Task Assignment & Reassignment**:
   - Assign unassigned task to Member A.
   - Reassign task from Member A to Member B.
   - Unassign task (`assigned_to = NULL`) and verify it remains on the Home board.
4. **Task Update & Optimistic Concurrency**:
   - Update title and due date with version matching.
   - Attempt update with mismatched version $\rightarrow$ returns HTTP 409 Conflict.

### 2.2 Date Derivations & Views
5. **Overdue Derivation**: Task with past due date ($\text{due\_date} < \text{today}$) and `status = 'TODO'` returns `is_overdue = True`.
6. **Due Today Derivation**: Task with today's date returns `is_due_today = True`.
7. **Upcoming Derivation**: Task with future date returns `is_upcoming = True`.
8. **View Filtering**:
   - Query `?view=my_tasks` as Member A $\rightarrow$ returns only tasks assigned to Member A.
   - Query `?view=overdue` $\rightarrow$ returns only overdue tasks.
   - Query `?view=completed` $\rightarrow$ returns historical completed tasks.

### 2.3 Recurrence Engine & Completion
9. **One-Time Task Completion**:
   - Complete non-recurring task.
   - Verify `status = 'COMPLETED'`, `completed_by = current_user.id`, `completed_at = NOW()`.
   - Verify no new task is spawned.
10. **Recurring Task Completion (Scheduled Date Base)**:
    - Task due on 15th with `recurrence_type = 'MONTHLY'`, `recurrence_strategy = 'SCHEDULED_DATE'`.
    - Complete task on 17th.
    - Verify current task transitions to `COMPLETED`.
    - Verify next task created with `due_date = 15th of next month`.
11. **Recurring Task Completion (Completion Date Base)**:
    - Task with `recurrence_type = 'CUSTOM_DAYS'`, `interval_days = 30`, `recurrence_strategy = 'COMPLETION_DATE'`.
    - Complete task today.
    - Verify next task created with `due_date = today + 30 days`.
12. **Double Completion Prevention**:
    - Attempting to complete an already completed task returns HTTP 400 Bad Request.

### 2.4 Task Templates Catalog
13. **Task Templates Listing**: Retrieve global templates catalog (Water filter, AC service, etc.).
14. **Template Selection**: Create task from template; verify pre-filled title, category, and recurrence interval.

### 2.5 Security & Multi-Home Isolation
15. **Cross-Home Access Rejection**: User in Home A cannot read, edit, or complete Home B tasks (HTTP 403 Forbidden).
16. **Client Creator Spoofing Rejection**: Payload attempting to set arbitrary `created_by` or `completed_by` is overridden by authenticated user session.
17. **Role-Based Permissions**: Unverified mobile accounts or non-members receive HTTP 403.
