# Ozhzo Verse — Phase 4: Tasks & Household Responsibilities Data Model

## 1. Relational DDL Schema

```sql
-- 1. Task Categories (Configurable)
CREATE TABLE IF NOT EXISTS task_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_task_categories_home_name UNIQUE (home_id, name)
);

-- 2. Task Templates (Common Household Tasks Catalog)
CREATE TABLE IF NOT EXISTS task_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL UNIQUE,
    default_category_name VARCHAR(100) NOT NULL DEFAULT 'Maintenance',
    default_priority VARCHAR(16) NOT NULL DEFAULT 'NORMAL',
    default_recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, CUSTOM_DAYS
    default_interval_days INTEGER NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    template_id UUID NULL REFERENCES task_templates(id) ON DELETE SET NULL,
    category_id UUID NULL REFERENCES task_categories(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH, URGENT
    status VARCHAR(32) NOT NULL DEFAULT 'TODO', -- TODO, IN_PROGRESS, COMPLETED, CANCELLED
    due_date TIMESTAMP WITH TIME ZONE NULL,
    recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days INTEGER NULL,
    recurrence_strategy VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED_DATE', -- SCHEDULED_DATE, COMPLETION_DATE
    parent_recurring_task_id UUID NULL REFERENCES tasks(id) ON DELETE SET NULL,
    assigned_to UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    completed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);
```

---

## 2. Performance & Indexing Strategy

```sql
-- Fast query by home, status, and due date
CREATE INDEX IF NOT EXISTS idx_tasks_home_status_due 
ON tasks (home_id, status, due_date) 
WHERE deleted_at IS NULL;

-- Fast query for assigned member's tasks ("My Tasks")
CREATE INDEX IF NOT EXISTS idx_tasks_home_assigned 
ON tasks (home_id, assigned_to, status) 
WHERE deleted_at IS NULL;

-- Fast completion history timeline
CREATE INDEX IF NOT EXISTS idx_tasks_home_completed_time 
ON tasks (home_id, completed_at DESC) 
WHERE status = 'COMPLETED';

-- Fast text search by title
CREATE INDEX IF NOT EXISTS idx_tasks_home_search 
ON tasks (home_id, title) 
WHERE deleted_at IS NULL;
```

---

## 3. Data Dictionary

### `tasks`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` | Owning Home tenant boundary (FK) |
| `template_id` | `UUID` (Nullable) | Origin template if selected from catalog |
| `category_id` | `UUID` (Nullable) | Category reference (e.g. Cleaning, Maintenance) |
| `title` | `VARCHAR(200)` | Task title (e.g. "Clean water filter") |
| `description` | `TEXT` | Detailed instructions / notes |
| `priority` | `VARCHAR(16)` | `LOW`, `NORMAL`, `HIGH`, `URGENT` (Default `NORMAL`) |
| `status` | `VARCHAR(32)` | `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| `due_date` | `TIMESTAMPTZ` | Scheduled completion deadline |
| `recurrence_type` | `VARCHAR(32)` | `NONE`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `CUSTOM_DAYS` |
| `recurrence_interval_days` | `INTEGER` | Custom interval in days (e.g. `30`, `180`) |
| `recurrence_strategy` | `VARCHAR(32)` | `SCHEDULED_DATE` vs `COMPLETION_DATE` |
| `parent_recurring_task_id` | `UUID` | Pointer to root recurring task definition |
| `assigned_to` | `UUID` (Nullable) | Family member assigned to execute task |
| `created_by` | `UUID` | Author of the task |
| `completed_by` | `UUID` (Nullable) | Member who checked off the task |
| `completed_at` | `TIMESTAMPTZ` | Timestamp of completion |
| `version` | `INTEGER` | Concurrency lock version |
