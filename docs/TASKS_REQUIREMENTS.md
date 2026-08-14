# Ozhzo Verse — Phase 4: Tasks & Household Responsibilities Requirements

## 1. Functional Requirements

### 1.1 Home-Scoped Task Management
- **FR-TASK-01**: Every Home possesses a unified task list where all authorized members can view, create, and collaborate.
- **FR-TASK-02**: Adding a task requires only `title` (minimum 2 characters).
- **FR-TASK-03**: Optional task attributes: `description`, `priority` (`LOW`, `NORMAL`, `HIGH`, default `NORMAL`), `assigned_to` (UUID of home member), `due_date` (TIMESTAMPTZ), `category_id` (UUID), `recurrence_type` (`NONE`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `CUSTOM_DAYS`), and `recurrence_interval_days` (int).

### 1.2 Status & Lifecycle
- **FR-STATE-01**: Valid Task States:
  - `TODO`: Pending action.
  - `IN_PROGRESS`: Actively being worked on by a member.
  - `COMPLETED`: Successfully executed.
  - `CANCELLED`: Dismissed or removed.
- **FR-STATE-02**: Completing a task captures `completed_by` (authenticated user ID) and `completed_at` (current timestamp).

### 1.3 Recurrence Engine
- **FR-REC-01**: Support standard household intervals:
  - `DAILY`: +1 day
  - `WEEKLY`: +7 days
  - `MONTHLY`: +30 days / same day next month
  - `CUSTOM_DAYS`: $+N$ days (e.g. 14 days, 45 days, 180 days for 6-month AC service).
- **FR-REC-02**: When a recurring task is completed:
  - Current task instance transitions to `COMPLETED`.
  - Next task occurrence is automatically created in `TODO` state with `due_date` computed from recurrence rules.
  - Idempotency guard prevents duplicate recurrence creation during concurrent completion requests.

### 1.4 Dynamic Views & Filtering
- **FR-VIEW-01**: Primary views:
  - `ALL`: All active tasks for the Home.
  - `TODAY`: Tasks where `due_date` is today.
  - `UPCOMING`: Tasks due in the future ($> \text{today}$).
  - `OVERDUE`: Tasks where $\text{due\_date} < \text{today}$ and $\text{status} \neq \text{COMPLETED}$.
  - `MY_TASKS`: Tasks assigned to the currently logged-in member.
  - `COMPLETED`: Searchable history of completed household tasks.

### 1.5 Task Templates
- **FR-TPL-01**: Support ready-to-use household task templates (e.g. *Clean water filter*, *AC Service*, *Car Maintenance*, *Deep clean kitchen*, *Smoke detector battery check*).
- **FR-TPL-02**: Selecting a template pre-fills task title, category, default priority, and recommended recurrence interval.

---

## 2. Non-Functional Requirements

### 2.1 Security & RBAC
- **NFR-SEC-01**: Every endpoint enforces `require_home_permission(...)`.
  - `tasks:view`: View home tasks and history.
  - `tasks:create`: Create new tasks.
  - `tasks:edit`: Update task details, priority, or due date.
  - `tasks:complete`: Check off and complete tasks.
  - `tasks:delete`: Cancel or delete tasks.
- **NFR-SEC-02**: Cross-home access attempts return `403 Forbidden`.
- **NFR-SEC-03**: Server always resolves `created_by` and `completed_by` from the authenticated session.

### 2.2 Concurrency & Idempotency
- **NFR-CONC-01**: Optimistic locking with integer `version` field prevents lost updates during simultaneous family edits.
- **NFR-CONC-02**: Completing an already completed task returns HTTP 400 Bad Request.

### 2.3 Performance & Indexing
- **NFR-PERF-01**: Task list queries must execute in $< 25\text{ms}$ at p95 for up to 1,000 tasks per Home.
- **NFR-PERF-02**: Composite index on `(home_id, status, due_date)`.
