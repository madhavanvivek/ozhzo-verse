# Ozhzo Verse — Phase 6: Shared Calendar & Household Events Requirements

## 1. Functional Requirements

### 1.1 Home Event Management
- **FR-CAL-01**: Every Home maintains a shared calendar of family events, appointments, and domestic routines.
- **FR-CAL-02**: Quick Add requires only `title`, `start_time`, and `end_time` (or `is_all_day = true` with a date).
- **FR-CAL-03**: Optional event fields: `description`, `location` (plain text string), `category_id`, `is_all_day`, `reminder_minutes_before`, `recurrence_type` (`NONE`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `CUSTOM_DAYS`), `recurrence_interval_days`, `participant_user_ids`.

### 1.2 All-Day & Multi-Day Events
- **FR-CAL-04**: An event marked `is_all_day = true` spans full calendar days without requiring arbitrary start/end hour times.
- **FR-CAL-05**: Multi-day trips or visitors are supported with start and end date boundaries spanning multiple days.

### 1.3 Participants & Household Members
- **FR-CAL-06**: Events can link one or more household members as participants (`event_participants`).
- **FR-CAL-07**: Participant status tracks `INVITED`, `ACCEPTED`, `DECLINED`.
- **FR-CAL-08**: Assigning participants strictly validates that each user is an active member of the same Home.

### 1.4 Recurring Events
- **FR-CAL-09**: Reuses Phase 4/5 recurrence model (`SCHEDULED_DATE`) for repeating routines, birthdays, anniversaries, and annual holidays.
- **FR-CAL-10**: Editing or cancelling single occurrences vs recurring series follows a clean, non-conflicting model.

### 1.5 Dynamic Categories
- **FR-CAL-11**: Configurable categories (`Family`, `Birthday`, `Anniversary`, `School`, `Appointment`, `Travel`, `Holiday`, `Visitors`, `Maintenance`, `Social`, `Other`).

### 1.6 Unified Temporal Projection
- **FR-PROJ-01**: The system MUST provide an aggregated schedule projection endpoint returning events, due tasks, and due bills in a unified chronological stream.
- **FR-PROJ-02**: Underlying records remain decoupled in their respective domain tables (`events`, `tasks`, `bills`).

---

## 2. Non-Functional Requirements

### 2.1 Security & Multi-Home Isolation
- **NFR-SEC-01**: All calendar endpoints enforce `require_home_permission(...)`.
  - `calendar:view`: All active home members.
  - `calendar:create`, `calendar:edit`: `OWNER`, `ADMIN`, `MEMBER`.
  - `calendar:delete`: `OWNER`, `ADMIN`.
- **NFR-SEC-02**: Cross-home access returns `HTTP 403 Forbidden`.
- **NFR-SEC-03**: Authorship (`created_by`) is authoritatively resolved from the authenticated JWT session.

### 2.2 Concurrency & Time Integrity
- **NFR-CONC-01**: Optimistic concurrency locking via `version` column on `events`.
- **NFR-TIME-01**: All timestamps stored in UTC (`TIMESTAMPTZ`). Display formats converted using `homes.timezone`.
- **NFR-VAL-01**: End time cannot precede start time (`end_time >= start_time`).
