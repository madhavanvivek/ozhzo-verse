# Ozhzo Verse — Phase 6: Shared Calendar & Household Events UX Design

## 1. UX Principles & Interaction Architecture

1. **At-a-Glance Household Temporal Awareness**:
   - Family members should immediately understand what is happening today and this week across the entire home.
2. **Unified Timeline Projection**:
   - Color-coded badges and icons distinguish **Events** (Indigo/Family), **Tasks** (Emerald/Household), and **Bills** (Amber/Financial).
3. **Frictionless Quick Add**:
   - Direct inline quick-add bar on Web and Mobile for rapid domestic entry.
4. **Clean Mobile-First Agenda Layout**:
   - Optimized for touch screens, vertical scrolling, and swipe navigation between weeks/months.

---

## 2. Web Layout & Visual Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📅 HOME CALENDAR & SCHEDULE                        [ Month ▾ ] [ + Add Event ]│
│ What's happening in our home • Synchronized events, routines, and deadlines│
├─────────────────────────────────────────────────────────────────────────────┤
│  [ Today (2) ]  [ This Week (8) ]  [ Events Only ]  [ Tasks ]  [ Bills ]    │
├─────────────────────────────────────────────────────────────────────────────┤
│ ➕ Quick Add: [ Event title...           ] [ Date/Time ] [ Location ] [ Add ]│
│    Presets: [ + Doctor Visit ] [ + Birthday ] [ + School Event ] [ + Trip ] │
├─────────────────────────────────────────────────────────────────────────────┤
│ TODAY — FRIDAY, 15 AUGUST                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 🎂 ALL DAY  Grandmother's 80th Birthday                                 │ │
│ │    Location: Family Home • Participants: Vivek, Karthika                │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ⚡ BILL DUE  BESCOM Electricity Bill (₹2,000.00)                        │ │
│ │    Responsible: Vivek • Status: Unpaid                                  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ TOMORROW — SATURDAY, 16 AUGUST                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 🕒 10:00 AM  Parent-Teacher Meeting (Term 1 Review)                     │ │
│ │    Location: Oakridge School Room 204 • Participants: Karthika          │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 🧹 TASK DUE  Clean Water Filter Replacement                             │ │
│ │    Assigned: Vivek • Status: Todo                                       │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mobile Screens & Flow

1. **Agenda Screen**:
   - Top weekly date strip with dot indicators for busy days.
   - Grouped chronological list of daily cards.
   - Floating Action Button (FAB) `+` opens quick bottom sheet.
2. **Add Event Bottom Sheet**:
   - Single-screen flow with Title input, Date picker, All-day toggle, Location string, and Member chip selector.
3. **Event Detail Sheet**:
   - Displays time, location, attendees with RSVP status (`Accept` / `Decline`), reminder lead-time, and edit/cancel options.
