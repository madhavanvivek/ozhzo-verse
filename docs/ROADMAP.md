# Product Roadmap & Phased Execution — Ozhzo Verse

## 1. Roadmap Overview

The development of Ozhzo Verse is phased to systematically eliminate technical and product risk, starting with foundational data isolation and culminating in public multi-member household validation.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PHASE 0    │ ──► │   PHASE 1    │ ──► │   PHASE 2    │ ──► │   PHASE 3    │ ──► │   PHASE 4    │
│ Foundations  │     │ Identity &   │     │ 5 Activity   │     │ Dashboard &  │     │ Alpha Pilot  │
│ & Spec Baseline│   │ Home RBAC    │     │ Core Pillars │     │ Notifications│     │ & Dogfooding │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                                           │
                                                                                           ▼
                                                        ┌──────────────┐            ┌──────────────┐
                                                        │   PHASE 6+   │ ◄───────── │   PHASE 5    │
                                                        │ Connected    │            │ Public Beta  │
                                                        │ Home OS (V2) │            │ & Subscriptions
                                                        └──────────────┘            └──────────────┘
```

---

## 2. Phase-by-Phase Breakdown

### Phase 0: Architectural Baseline & Specs (Current Phase)
- **Goal**: Lock down product vision, scope boundaries, database schemas, RBAC matrix, and API contracts.
- **Deliverables**:
  - Comprehensive documentation in `/docs` (12 source-of-truth documents).
  - Agreement on non-negotiable product and engineering principles.
  - Identification and escalation of foundational product decisions for Founder approval.

---

### Phase 1: Identity, Home Workspaces & Multi-Tenancy Engine
- **Goal**: Implement rock-solid authentication, profile management, home creation, multi-home switching, and invite-based member onboarding.
- **Deliverables**:
  - FastAPI auth service with JWT rotation, registration, login, and password management.
  - Multi-tenant Home management API with tenant context resolution and RBAC middleware.
  - Next.js and Flutter authentication flows and Home Switcher components.
  - Member invitation engine with time-expiring tokens.
  - Automated multi-tenancy isolation unit and integration test suite.

---

### Phase 2: The Five Core Operational Pillars
- **Goal**: Build the primary everyday modules that replace fragmented household tools.
- **Deliverables**:
  1. **Household Inventory**: Categorized pantry/fridge tracking, stock levels, low-threshold alarms, expiry date tracking.
  2. **Shopping Lists**: Real-time interactive shopping lists with aisle grouping and one-tap inventory restocking.
  3. **Tasks & Chores**: Chore allocation, recurring schedules, priority tagging, and personal assignment views.
  4. **Bills & Reminders**: Recurring utility tracking, payment records, due date reminders, and archive ledgers.
  5. **Calendar & Events**: Shared family event calendar with RSVP attendance.

---

### Phase 3: Dashboard Aggregation & Proactive Notification Engine
- **Goal**: Synthesize household state into a single cohesive morning dashboard and deliver timely alerts.
- **Deliverables**:
  - Home Dashboard API with single-trip aggregated pulse endpoint.
  - Background scheduler (Celery / Redis / APScheduler) for cron evaluations of expiring items, due chores, and upcoming bills.
  - Multi-channel notification engine (in-app inbox, web push, mobile push via APNs/FCM).

---

### Phase 4: Private Alpha & Internal Household Dogfooding
- **Goal**: Validate usability and data integrity across 15–25 real test households.
- **Deliverables**:
  - Dogfooding telemetry and feedback loops.
  - Latency optimization and database query profiling.
  - Bug fixes and UX polish based on real family member feedback.

---

### Phase 5: Public Beta & Subscription Monetization Foundation
- **Goal**: Release to early adopters and establish payment infrastructure.
- **Deliverables**:
  - Free vs. Premium tier gating (e.g. member limits, storage, advanced recurrence).
  - Stripe billing integration for Home subscriptions.
  - Public onboarding marketing funnel.

---

### Phase 6+: Post-MVP Expansion Horizon (Future Vision)
- **Goal**: Expand from single-home workspace to interconnected Home OS ecosystem.
- **Capabilities (Strictly Post-MVP)**:
  - Connected Homes & trusted home-to-home circles (extended family/neighbors).
  - Cross-home item borrowing and lending ledger.
  - Local home services marketplace and verified technician scheduling.
  - IoT and smart home appliance telemetry integration (Matter / Zigbee).
  - Privacy-first AI household assistant.
