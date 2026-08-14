# Ozhzo Verse — Phase 7: MVP Experience & Integration Architecture

**Document**: Phase 7 Architecture & Integration Framework  
**Classification**: Definitive Integration Source of Truth  
**Target**: Product Leads, Full-Stack Architects, Frontend/Mobile Engineers  

---

## 1. Executive Purpose & Product Principles

Ozhzo Verse is the **Digital Memory and Operating System for the Home**. 

Between Phase 2 and Phase 6, we designed and built the individual specialized pillars of the household:
- **Phase 2**: Multi-Home workspace tenancy, membership, invitations, RBAC.
- **Phase 3A**: Inventory supplies, durable assets, hierarchical locations, location movement history, asset lending/return.
- **Phase 3B**: Home purchase lists, global inventory templates, unit master, home customization.
- **Phase 4**: Tasks & household responsibilities, assignments, recurrence, completion history.
- **Phase 5**: Bills & recurring expenses, payments, partial balances, financial ledger.
- **Phase 6**: Shared calendar, household events, participant tracking, dynamic temporal projection.

**Phase 7 does NOT introduce new domain models or separate databases.**  
Instead, Phase 7 orchestrates these frozen domains into **ONE unified, cohesive domestic experience** answering the 9 central household questions:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          THE OZHZO DIGITAL HOME OS                          │
│                                                                             │
│  1. WHAT DO WE HAVE?        ──►  Inventory & Durable Assets (Phase 3A)      │
│  2. WHERE IS IT?            ──►  Hierarchical Location Memory (Phase 3A)    │
│  3. WHO HAS IT?             ──►  Asset Lending Ledger (Phase 3A)            │
│  4. WHAT DO WE NEED?        ──►  Home Purchase List (Phase 3B)              │
│  5. WHAT NEEDS TO BE DONE?  ──►  Tasks & Household Routines (Phase 4)       │
│  6. WHO IS RESPONSIBLE?     ──►  Assigned Member / Responsible Person       │
│  7. WHAT DO WE HAVE TO PAY? ──►  Bills & Financial Obligations (Phase 5)    │
│  8. WHAT IS HAPPENING TODAY?──►  Unified Today View & Calendar (Phase 6/7)  │
│  9. WHAT NEEDS MY ATTENTION?──►  Attention Center & Real-Time Pulse (Phase 7│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architectural Cohesion Model (Zero Data Duplication)

The foundational design rule of Phase 7 is: **Projections over Duplication**.

```mermaid
graph TD
    subgraph Household Domain Pillars (Frozen Data Stores)
        Inv[(Inventory & Assets)]
        Shop[(Purchase Lists)]
        Task[(Tasks & Chores)]
        Bill[(Bills & Payments)]
        Event[(Calendar Events)]
        Audit[(Audit & Movement Logs)]
    end

    subgraph Phase 7 Unified Integration Services
        TodaySvc[Unified Today Engine]
        SearchSvc[Global Home Memory & Search]
        AttentionSvc[Attention & Alert Center]
        ActivitySvc[Home Activity Feed]
        QuickAddSvc[Global Quick Add Gateway]
        DashSvc[Home Dashboard Aggregator]
    end

    subgraph Client Experiences
        Web[Web Next.js Dashboard & Modals]
        Mobile[Mobile Flutter Experience]
    end

    Inv --> TodaySvc
    Task --> TodaySvc
    Bill --> TodaySvc
    Event --> TodaySvc

    Inv --> SearchSvc
    Shop --> SearchSvc
    Task --> SearchSvc
    Bill --> SearchSvc
    Event --> SearchSvc

    Inv --> AttentionSvc
    Task --> AttentionSvc
    Bill --> AttentionSvc

    Audit --> ActivitySvc
    Inv --> ActivitySvc
    Task --> ActivitySvc
    Bill --> ActivitySvc

    TodaySvc --> DashSvc
    AttentionSvc --> DashSvc
    ActivitySvc --> DashSvc

    DashSvc --> Web
    DashSvc --> Mobile
    SearchSvc --> Web
    SearchSvc --> Mobile
    QuickAddSvc --> Web
    QuickAddSvc --> Mobile
```

1. **No Phantom Records**: No new tables are created simply to display "Today", "Search", or "Attention".
2. **Deterministic Aggregation**: All integration views query the underlying domain repositories dynamically, applying server-authoritative tenant scoping (`WHERE home_id = :home_id`).
3. **Discriminator & Navigation Targets**: Every projected item returns:
   - `source_type`: `INVENTORY`, `ASSET`, `PURCHASE`, `TASK`, `BILL`, `EVENT`, `LOCATION`, `MEMBER`.
   - `source_id`: The canonical UUID of the underlying record.
   - `navigation_target`: Deep-link path (e.g. `/inventory/items/{id}`, `/tasks/{id}`, `/bills/{id}`).
   - `editable`: Direct editability flag (e.g. `true` for events from calendar, `false` for task projections requiring task modal).

---

## 3. Scope Boundaries & Anti-Bloat Rules

To ensure a razor-sharp MVP delivery:
- **NO AI/Chatbots**: Do not introduce conversational LLM bots or unstructured chat in this phase.
- **NO Vector/Semantic Search**: Search is high-speed deterministic prefix, substring, and hierarchical token matching with composite indexing.
- **NO External Banking/Payment Gateways**: Financial tracking remains an immutable ledger recording domestic cash/UPI/card settlement events.
- **NO External CalDAV/Google Calendar Sync**: The Home Calendar is an internal domestic coordination hub.
- **NO Connected Home / IoT Protocol Stacks**: No MQTT, Matter, or Zigbee device integration in Phase 7.
