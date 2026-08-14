# MVP Scope & Feature Specification — Ozhzo Verse

*Document Classification: Definitive Source of Truth*  
*Target Audience: Product Managers, Engineers, QA, Leadership*

---

## 1. Scope Boundary & Core Objective

The Ozhzo Verse Minimum Viable Product (MVP) is engineered to validate one singular hypothesis:

> **"Can a household use Ozhzo Verse as a unified, shared digital workspace to manage their daily home activities (chores, groceries, inventory, bills, and schedule) with less friction and greater alignment than existing ad-hoc tools?"**

Every admitted feature is classified under the **MoSCoW framework** (Must Have, Should Have, Could Have, Not in MVP).

---

## 2. MUST HAVE Features (P0 — Non-Negotiable Core)

These features represent the critical operational backbone. Without them, the MVP cannot be launched.

### Module 1: Authentication & Identity

#### `AUTH-01`: Email & Password Authentication with JWT Rotation
- **Purpose**: Provide secure user registration, credential login, and session persistence.
- **User Value**: Users can securely create personal accounts and stay logged in across devices.
- **Priority**: `MUST HAVE`
- **Dependencies**: None (Foundational)
- **Acceptance Criteria**:
  1. Users can register with email and strong password (min 8 chars, 1 number, 1 special).
  2. Passwords hashed using Argon2id / bcrypt.
  3. Returns short-lived JWT access token (15m) and secure HTTP-only refresh token (30d).
  4. Supports token refresh endpoint and secure logout with server-side token revocation.

#### `AUTH-02`: Password Reset Workflow
- **Purpose**: Allow users to regain account access when credentials are forgotten.
- **User Value**: Prevents permanent account abandonment.
- **Priority**: `MUST HAVE`
- **Dependencies**: `AUTH-01`, Email Service
- **Acceptance Criteria**:
  1. User enters registered email; system dispatches time-limited (15-minute) reset token.
  2. Reset link validates token and allows setting a new password.
  3. All existing active sessions for that user are revoked upon password reset.

---

### Module 2: User Profile

#### `PROF-01`: Basic User Profile Management
- **Purpose**: Maintain user identity, display name, contact info, and default timezone.
- **User Value**: Household members can identify each other with real names and avatars.
- **Priority**: `MUST HAVE`
- **Dependencies**: `AUTH-01`
- **Acceptance Criteria**:
  1. User can view and update display name, avatar image URL, and primary timezone.
  2. Timezone automatically detected during client onboarding and stored.

---

### Module 3: Home Creation & Context

#### `HOME-01`: Home Workspace Provisioning
- **Purpose**: Create and configure the primary `Home` organizational entity.
- **User Value**: Gives the household a dedicated, isolated digital workspace.
- **Priority**: `MUST HAVE`
- **Dependencies**: `AUTH-01`, `PROF-01`
- **Acceptance Criteria**:
  1. Authenticated user can create a Home with Name, Currency (USD, EUR, INR, etc.), and Timezone.
  2. The creator is automatically assigned the `OWNER` role.
  3. A user can create and belong to multiple homes.

#### `HOME-02`: Multi-Home Context Switching
- **Purpose**: Enable seamless switching between multiple homes (e.g., Primary Home vs. Cabin).
- **User Value**: Users managing multiple households do not need multiple logins.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`
- **Acceptance Criteria**:
  1. Top-bar/header home switcher displays all homes the user belongs to.
  2. Switching active home updates client context and invalidates tenant-scoped cache.
  3. All subsequent queries strictly execute against the selected `home_id`.

---

### Module 4: Home Members & Invites

#### `MEMB-01`: Secure Member Invitation Engine
- **Purpose**: Invite family members or roommates to join the home workspace.
- **User Value**: Onboards co-habitants into the shared environment.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`, `AUTH-01`
- **Acceptance Criteria**:
  1. Owner or Admin can generate an invite link or enter an email.
  2. Invite tokens expire after 7 days and can be revoked by Admins.
  3. Joining user accepts invite and receives assigned role (`ADMIN`, `MEMBER`, `LIMITED_MEMBER`).

#### `MEMB-02`: Member List & Removal
- **Purpose**: Manage existing household member roster.
- **User Value**: Maintain clear visibility and control over who has access to home data.
- **Priority**: `MUST HAVE`
- **Dependencies**: `MEMB-01`
- **Acceptance Criteria**:
  1. Displays all members with display name, avatar, role, and join date.
  2. Owners/Admins can remove non-owner members; removed members lose instant access.
  3. Members can voluntarily leave a home.

---

### Module 5: Roles & Permissions (RBAC)

#### `RBAC-01`: Home-Scoped Role Enforcement
- **Purpose**: Enforce operational boundaries across `OWNER`, `ADMIN`, `MEMBER`, and `LIMITED_MEMBER`.
- **User Value**: Protects sensitive financial data and home settings from unintended modification.
- **Priority**: `MUST HAVE`
- **Dependencies**: `MEMB-01`, `HOME-01`
- **Acceptance Criteria**:
  1. API service layer validates role permissions before executing any mutation.
  2. `LIMITED_MEMBER` cannot view bills, cannot delete inventory, and cannot invite members.
  3. Only `OWNER` can delete the home workspace or manage subscription billing.

---

### Module 6: Home Dashboard

#### `DASH-01`: Daily Pulse Aggregation Hub
- **Purpose**: Synthesize household state into a single morning view.
- **User Value**: Instant visibility into what needs attention today without navigating 5 modules.
- **Priority**: `MUST HAVE`
- **Dependencies**: `TASK-01`, `INV-01`, `BILL-01`, `CAL-01`
- **Acceptance Criteria**:
  1. Displays summary cards: Chores Due Today, Low Stock Items, Upcoming Bills (next 7d), Today's Events.
  2. Single-trip aggregated API endpoint (`GET /homes/{home_id}/dashboard`) loads in under 300ms.
  3. Clicking any item deep-links directly to the respective module.

---

### Module 7: Household Inventory

#### `INV-01`: Categorized Inventory Tracking
- **Purpose**: Track household supplies, food, and pantry items with stock levels.
- **User Value**: Prevents duplicate purchases and running out of essential items.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`
- **Acceptance Criteria**:
  1. Supports standard categories: Pantry, Fridge, Freezer, Cleaning, Medicine, Other.
  2. Item includes Name, Category, Quantity, Unit (pcs, kg, L, etc.), and Min Threshold.
  3. Status computed dynamically: `IN_STOCK`, `LOW_STOCK` (when qty <= threshold), `OUT_OF_STOCK` (qty = 0).

#### `INV-02`: Expiry Date Tracking & Expiry Alerts
- **Purpose**: Track perishable items to prevent food waste.
- **User Value**: Saves money and reduces domestic food spoilage.
- **Priority**: `MUST HAVE`
- **Dependencies**: `INV-01`
- **Acceptance Criteria**:
  1. Optional expiry date picker per inventory item.
  2. Items expiring within 3 days are highlighted with an amber badge; expired items flagged in red.
  3. Expiring items surface on the Home Dashboard.

---

### Module 8: Shopping Lists

#### `SHOP-01`: Real-Time Collaborative Shopping Lists
- **Purpose**: Shared, interactive grocery checklists with live sync across family members.
- **User Value**: Family members at the supermarket can see real-time updates as items are bought.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`
- **Acceptance Criteria**:
  1. Support for multiple shopping lists per home (e.g. "Weekly Groceries", "Hardware").
  2. Interactive checkbox toggles `is_checked` status with visual strikethrough.
  3. Records who checked the item and when.
  4. Live sync updates all viewing family members within 1 second.

#### `SHOP-02`: Inventory-to-Shopping List Quick Add
- **Purpose**: Bridge inventory tracking with shopping execution.
- **User Value**: 1-tap conversion from "low stock" to "on the grocery list".
- **Priority**: `MUST HAVE`
- **Dependencies**: `INV-01`, `SHOP-01`
- **Acceptance Criteria**:
  1. Low stock inventory items display an "+ Add to Shopping List" action button.
  2. Added items link back to the inventory item ID.
  3. When an item is checked off in the shopping list, user is prompted: *"Update inventory to In Stock?"*.

---

### Module 9: Tasks & Chores

#### `TASK-01`: Task & Chore Management
- **Purpose**: Create, assign, and track domestic responsibilities with due dates and priorities.
- **User Value**: Eliminates chore ambiguity and ensures equitable household participation.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`, `MEMB-01`
- **Acceptance Criteria**:
  1. Task includes Title, Description, Priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), Due Date/Time, Assignee.
  2. Tasks can be assigned to a specific member or marked unassigned ("Anyone").
  3. 1-tap task completion moves item to Completed archive with completion timestamp.

#### `TASK-02`: Recurring Chores Engine
- **Purpose**: Automate repeating household chores (e.g. "Take out trash every Monday").
- **User Value**: Eliminates manual chore re-creation.
- **Priority**: `MUST HAVE`
- **Dependencies**: `TASK-01`
- **Acceptance Criteria**:
  1. Supports standard recurrence rules: Daily, Weekly (specific days), Monthly.
  2. When a recurring task instance is completed, the next instance is generated automatically.

---

### Module 10: Bills & Reminders

#### `BILL-01`: Recurring Bill Tracker
- **Purpose**: Centralize household utility, rent, and subscription bills.
- **User Value**: Prevents late payment penalties and provides financial clarity for the home.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`
- **Acceptance Criteria**:
  1. Records Bill Title, Category (Electricity, Water, Internet, Rent), Amount, Currency, Due Date, Recurrence.
  2. Status tracks `UNPAID`, `PAID`, and automatically flags `OVERDUE` when current date > due date.
  3. Visible to Owner, Admin, and Member roles; hidden from Limited Members.

#### `BILL-02`: Payment Settlement Recording
- **Purpose**: Log bill payments and preserve an audit ledger.
- **User Value**: Eliminates "Did you pay this?" domestic confusion.
- **Priority**: `MUST HAVE`
- **Dependencies**: `BILL-01`
- **Acceptance Criteria**:
  1. Any authorized member can mark a bill as Paid, recording paid amount, date, and reference note.
  2. For recurring bills, marking paid advances the bill to the next due cycle.
  3. Preserves a searchable payment history log.

---

### Module 11: Calendar & Events

#### `CAL-01`: Shared Household Calendar
- **Purpose**: Unified schedule for family milestones, appointments, and home maintenance.
- **User Value**: Prevents scheduling conflicts between household members.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`
- **Acceptance Criteria**:
  1. Create events with Title, Date/Time range, All-Day flag, Location/Notes, and Category.
  2. Monthly and Weekly agenda views.
  3. Integrated display of chore deadlines and bill due dates alongside calendar events.

---

### Module 12: Notifications

#### `NOTIF-01`: In-App Notification Center
- **Purpose**: Centralized inbox for domestic alerts and assignments.
- **User Value**: Ensures users never miss actionable household events.
- **Priority**: `MUST HAVE`
- **Dependencies**: `TASK-01`, `BILL-01`, `INV-01`, `MEMB-01`
- **Acceptance Criteria**:
  1. Notification inbox displays alerts: Task Assigned, Task Due Soon, Bill Due (T-3 days), Low Stock, Invite.
  2. Mark as read / Mark all read functionality.
  3. Badge count indicator on app header.

---

### Module 13: Subscription Foundation

#### `SUB-01`: Free vs. Premium Tier Gating Engine
- **Purpose**: Establish architectural tier enforcement for monetization readiness.
- **User Value**: Free users enjoy full core utility while clear premium boundaries are established.
- **Priority**: `MUST HAVE`
- **Dependencies**: `HOME-01`
- **Acceptance Criteria**:
  1. **Free Tier**: 1 Home workspace, up to 5 members, 100 inventory items.
  2. **Premium Tier**: Unlimited members, multiple homes, unlimited inventory history.
  3. Gating logic implemented as backend middleware; gracefully prompts upgrade when limits reached.

---

## 3. SHOULD HAVE Features (P1 — High Value for Polish)

These features enhance engagement and usability, targeted for inclusion in the MVP launch or immediate v1.1.

| Feature ID | Feature Name | Purpose | User Value | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `NOTIF-02` | **Mobile Push Notifications (APNs / FCM)** | Deliver device push alerts. | Timely alerts even when app is closed. | `NOTIF-01` | Push sent for due chores, urgent bills, and new invites. |
| `SHOP-03` | **Aisle / Store Category Grouping** | Group grocery items by aisle (Produce, Dairy). | Faster, structured in-store navigation. | `SHOP-01` | Items automatically grouped by store section. |
| `TASK-03` | **Chore Completion Streaks & Stats** | Track consecutive chore completions. | Positive reinforcement for teens/family. | `TASK-01` | Displays active household streak counter. |
| `DASH-02` | **Recent Activity Feed** | Audit log of recent actions. | Transparency into who did what today. | `DASH-01` | Stream of last 20 actions (checked items, chores). |
| `INV-03` | **Bulk Quick Stock Quantity Adjuster** | Rapid `+` / `-` stock counter. | Fast inventory updates without opening detail modal. | `INV-01` | Inline increment/decrement buttons on inventory list. |

---

## 4. COULD HAVE Features (P2 — Stretch / Post-Launch Fast Follows)

Features that provide additional convenience but can be deferred without degrading MVP validation.

| Feature ID | Feature Name | Purpose | User Value | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `INV-04` | **Barcode Scanner for Inventory** | Scan UPC barcode to auto-populate item name. | Reduces manual typing for packaged groceries. | `INV-01` | Scans standard UPC/EAN barcode via mobile camera. |
| `CAL-02` | **External Calendar Export (.ics)** | Export household calendar to Google/Apple Calendar. | Integrates home events into personal work calendars. | `CAL-01` | Generates a read-only `.ics` calendar subscription feed. |
| `BILL-03` | **Receipt Image Attachment** | Attach photo of utility bill/receipt. | Visual proof of payment. | `BILL-02` | Upload image (max 5MB) attached to bill payment record. |
| `PROF-02` | **Dark Mode Theme Support** | System-matching dark appearance. | Visual comfort in low-light environments. | Design System | Flawless dark mode toggle matching token palette. |

---

## 5. NOT IN MVP (Explicit Non-Goals & Future Horizon)

The following capabilities are **STRICTLY PROHIBITED** from MVP development:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXPLICIT OUT-OF-SCOPE FEATURES                        │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│ • Connected Homes        │ • Home-to-Home Following │ • Cross-Home Borrowing│
│ • Community Feeds        │ • Services Marketplace   │ • On-Demand Handymen  │
│ • IoT / Smart Appliances │ • Voice Assistants       │ • Advanced GenAI      │
│ • Matter/Zigbee Bridges  │ • In-App Money Transfers │ • P2P Crypto/Wallets  │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

*Rationale*: Every item above introduces external third-party dependencies, complex physical logistics, hardware fragmentation, or unvalidated social mechanics that would derail the core mission of validating the single-home operational workspace.

---

## 6. MVP Feature Freeze List

The following 17 P0 features and 5 P1 features constitute the **Locked MVP v1.0 Release Baseline**. No new features may be added to this list without formal architectural change review:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LOCKED MVP FEATURE FREEZE MATRIX                      │
├────────────┬─────────────────────────────────────────────────┬──────────────┤
│ MODULE     │ FEATURE ID & NAME                               │ PRIORITY     │
├────────────┼─────────────────────────────────────────────────┼──────────────┤
│ Auth       │ AUTH-01: Email/Password Auth & JWT Rotation     │ MUST (P0)    │
│ Auth       │ AUTH-02: Password Reset Workflow                │ MUST (P0)    │
│ Profile    │ PROF-01: Basic User Profile Management          │ MUST (P0)    │
│ Home       │ HOME-01: Home Workspace Provisioning            │ MUST (P0)    │
│ Home       │ HOME-02: Multi-Home Context Switching           │ MUST (P0)    │
│ Members    │ MEMB-01: Secure Member Invitation Engine        │ MUST (P0)    │
│ Members    │ MEMB-02: Member List & Removal                  │ MUST (P0)    │
│ RBAC       │ RBAC-01: Home-Scoped Role Enforcement           │ MUST (P0)    │
│ Dashboard  │ DASH-01: Daily Pulse Aggregation Hub            │ MUST (P0)    │
│ Dashboard  │ DASH-02: Recent Activity Feed                   │ SHOULD (P1)  │
│ Inventory  │ INV-01: Categorized Inventory Tracking          │ MUST (P0)    │
│ Inventory  │ INV-02: Expiry Date Tracking & Alerts           │ MUST (P0)    │
│ Inventory  │ INV-03: Bulk Quick Stock Quantity Adjuster      │ SHOULD (P1)  │
│ Shopping   │ SHOP-01: Real-Time Collaborative Shopping Lists │ MUST (P0)    │
│ Shopping   │ SHOP-02: Inventory-to-Shopping Quick Add        │ MUST (P0)    │
│ Shopping   │ SHOP-03: Aisle / Store Category Grouping        │ SHOULD (P1)  │
│ Tasks      │ TASK-01: Task & Chore Management                │ MUST (P0)    │
│ Tasks      │ TASK-02: Recurring Chores Engine                │ MUST (P0)    │
│ Tasks      │ TASK-03: Chore Completion Streaks & Stats       │ SHOULD (P1)  │
│ Bills      │ BILL-01: Recurring Bill Tracker                 │ MUST (P0)    │
│ Bills      │ BILL-02: Payment Settlement Recording           │ MUST (P0)    │
│ Calendar   │ CAL-01: Shared Household Calendar               │ MUST (P0)    │
│ Notifs     │ NOTIF-01: In-App Notification Center            │ MUST (P0)    │
│ Notifs     │ NOTIF-02: Mobile Push Notifications (APNs/FCM)  │ SHOULD (P1)  │
│ Subs       │ SUB-01: Free vs. Premium Tier Gating Engine     │ MUST (P0)    │
└────────────┴─────────────────────────────────────────────────┴──────────────┘
```
