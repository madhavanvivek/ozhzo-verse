# Ozhzo Verse — Phase 6: Shared Calendar & Household Events Data Model

## 1. Relational DDL Schema

```sql
-- 1. Event Categories (Configurable per Home)
CREATE TABLE IF NOT EXISTS event_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_event_categories_home_name UNIQUE (home_id, name)
);

-- 2. Events Table
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    category_id UUID NULL REFERENCES event_categories(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    location VARCHAR(255) NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_all_day BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days INTEGER NULL,
    parent_recurring_event_id UUID NULL REFERENCES events(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED', -- CONFIRMED, TENTATIVE, CANCELLED
    reminder_minutes_before INTEGER NULL DEFAULT 30,
    version INTEGER NOT NULL DEFAULT 1,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT chk_event_time_order CHECK (end_time >= start_time)
);

-- 3. Event Participants Table
CREATE TABLE IF NOT EXISTS event_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'INVITED', -- INVITED, ACCEPTED, DECLINED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_event_participants UNIQUE (event_id, user_id)
);
```

---

## 2. Performance & Indexing Strategy

```sql
-- Fast query by Home and Date Range
CREATE INDEX IF NOT EXISTS idx_events_home_timerange 
ON events (home_id, start_time, end_time) 
WHERE deleted_at IS NULL;

-- Fast query by Parent Recurring Event
CREATE INDEX IF NOT EXISTS idx_events_home_parent_recur 
ON events (home_id, parent_recurring_event_id) 
WHERE deleted_at IS NULL;

-- Fast lookup for Participant Events
CREATE INDEX IF NOT EXISTS idx_event_participants_user 
ON event_participants (user_id, event_id);
```

---

## 3. Data Dictionary

### `events`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` | Owning Home tenant boundary (FK) |
| `category_id` | `UUID` (Nullable) | Category FK |
| `title` | `VARCHAR(200)` | Event title (e.g. "Doctor Appointment") |
| `description` | `TEXT` (Nullable) | Detailed notes or agenda |
| `location` | `VARCHAR(255)` (Nullable) | Location text (e.g. "City Hospital Clinic 4B") |
| `start_time` | `TIMESTAMPTZ` | Start timestamp in UTC |
| `end_time` | `TIMESTAMPTZ` | End timestamp in UTC |
| `is_all_day` | `BOOLEAN` | If true, spans calendar days |
| `recurrence_type` | `VARCHAR(32)` | `NONE`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `CUSTOM_DAYS` |
| `recurrence_interval_days` | `INTEGER` | Custom interval in days |
| `parent_recurring_event_id` | `UUID` | Pointer to root series event |
| `status` | `VARCHAR(32)` | `CONFIRMED`, `TENTATIVE`, `CANCELLED` |
| `reminder_minutes_before` | `INTEGER` | Notification lead time |
| `version` | `INTEGER` | Concurrency lock version |
| `created_by` | `UUID` | User who created the event |

### `event_participants`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `event_id` | `UUID` | Associated Event (FK) |
| `user_id` | `UUID` | Home member user ID (FK) |
| `status` | `VARCHAR(20)` | `INVITED`, `ACCEPTED`, `DECLINED` |
