# Ozhzo Verse — Phase 4: Tasks & Household Responsibilities UI/UX Design

## 1. UX Design Philosophy
- **Frictionless Quick Add**: Adding a household task should require only typing the name and pressing Enter.
- **Clear Household Accountability**: Family members can clearly see what needs to be done for the Home and who is responsible.
- **Zero Corporate Fluff**: No kanban boards, story points, or complex sprint planning. Clean, readable checklist views organized by time urgency.

---

## 2. Key Screen Layouts & User Journeys

### 2.1 Web Tasks Dashboard
- **Top Summary Metrics**:
  - `Due Today` (e.g. 🔴 3 Due Today)
  - `Overdue` (e.g. ⚠️ 2 Overdue)
  - `Upcoming` (e.g. 🟢 9 Upcoming)
  - `My Tasks` (e.g. 👤 4 Assigned to Me)
- **Inline Quick Add Row**:
  - `[ Task Title... ] [ Assign Member ▾ ] [ Due Date ▾ ] [ Priority ▾ ] [ + Add Task ]`
- **Common Tasks Template Bar**:
  - Chips: `+ Clean Water Filter`, `+ Service AC`, `+ Change Bedsheets`, `+ Car Service`, `+ Pay School Fee`
- **Sectioned Task List**:
  - **OVERDUE** (Highlighted with warning accent)
    - `☐ ⚠️ Pay electricity bill — Overdue by 2 days • Assigned to Karthika`
  - **TODAY**
    - `☐ 🔴 Clean water filter — Due Today • Unassigned`
  - **UPCOMING**
    - `☐ 🟢 Service AC — Due 20 Aug • Assigned to Vivek`
    - `☐ 🟢 Change bedsheets — Due in 3 days • Repeats weekly`
  - **NO DUE DATE**
    - `☐ Organize storage cupboard — Low Priority`

### 2.2 Mobile Experience (Flutter)
- **Fast Daily Chore View**:
  - Segmented control: `Today` | `Upcoming` | `My Tasks` | `All`
  - Large $48\times 48\text{dp}$ touch target checkboxes for quick completion.
  - 1-tap swipe action to complete or reassign.

---

## 3. User Journeys

```
Journey 1: Quick Task Creation
Vivek notices water filter pressure is low ➔ Opens Ozhzo Tasks ➔ Types "Clean water filter" ➔ Taps Add ➔ Instantly visible to everyone.

Journey 2: Task Assignment & Execution
Karthika sees "Clean water filter" on Home Board ➔ Assigns it to herself ➔ Completes it ➔ Taps checkbox ➔ System logs "Completed by Karthika" and schedules next occurrence for 30 days later.

Journey 3: Morning Routine Check
Vivek opens mobile app ➔ Sees "2 Tasks Due Today" ➔ Checks off "Water front garden plants" ➔ Dashboard updates instantly.
```
