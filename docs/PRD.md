# Product Requirements Document (PRD) — Ozhzo Verse MVP

*Document Classification: Definitive Source of Truth*  
*Version: 1.0.0 (MVP Baseline)*  
*Target Audience: Product Managers, Software Engineers, QA Engineers, UX Architects*

---

## 1. Executive Summary & Scope Boundary

This Product Requirements Document (PRD) specifies the functional, behavioral, and architectural requirements for the Minimum Viable Product (MVP) of **Ozhzo Verse: The Digital Operating System for Homes**.

### MVP Core Objective
Validate whether households will adopt a unified digital workspace to organize daily chores, groceries, inventory, bills, and calendars with greater ease and alignment than ad-hoc tools.

---

## 2. Module Requirements Specifications

---

### Module 1: Authentication & Identity (`AUTH`)

#### 1. Objective
Provide secure, frictionless user registration, authentication, session lifecycle management, and credential recovery.

#### 2. User Problem
Users need a trustworthy, persistent account that allows them to access their homes securely across Web and Mobile devices.

#### 3. Actors
Unregistered User, Registered User, Authenticated User.

#### 4. User Stories
- **US-AUTH-01**: As a new user, I want to sign up with my email and password so that I can create or join a household workspace.
- **US-AUTH-02**: As a registered user, I want to log in securely and stay logged in so that I don't have to re-enter credentials every time I open the app.
- **US-AUTH-03**: As a user who forgot their password, I want to receive a secure reset link so that I can regain access to my account.

#### 5. Functional Requirements
- **`AUTH-001`**: The system MUST allow registration with Email, Full Name, and Password. Passwords must be hashed using Argon2id / bcrypt.
- **`AUTH-002`**: The system MUST authenticate valid credentials and issue a short-lived JWT access token (15m) and a secure HTTP-only refresh token (30d).
- **`AUTH-003`**: The system MUST provide a token refresh endpoint to exchange valid refresh tokens for new access tokens with token rotation.
- **`AUTH-004`**: The system MUST support password reset via time-limited (15m) single-use cryptographic tokens dispatched to the verified email.
- **`AUTH-005`**: The system MUST revoke all active sessions upon password reset or explicit logout.

#### 6. Business Rules
- Email addresses must be normalized to lowercase and trimmed before uniqueness verification.
- Passwords must be at least 8 characters long and contain at least 1 number and 1 special character.
- Failed login attempts are capped at 5 attempts per 15-minute window per IP to prevent brute-force attacks.

#### 7. Validation
- Email must conform to RFC 5322 format.
- Passwords shorter than 8 characters must return HTTP 422 Unprocessable Entity.

#### 8. Permissions
Publicly accessible endpoints (Rate-limited).

#### 9. Notifications
- Welcome / Verification Email upon registration.
- Password Reset Email upon request.
- Security alert email upon login from new device/IP.

#### 10. UI States
- **Empty State**: Clean login/register form with clear labels and autofocus on email.
- **Loading State**: Primary CTA button displays spinner with text "Authenticating...".
- **Error State**: Inline field alerts (e.g., *"Invalid email or password"*, *"Password must be at least 8 characters"*).

#### 11. Edge Cases
- User clicks password reset link after 15-minute expiration: Displays expired token error and offers to resend.
- Rapid successive refresh requests: Handled via atomic Redis token rotation lock.

#### 12. Acceptance Criteria
- Unit test verifies password hashing complexity and salt generation.
- Integration test verifies JWT issuance, expiry, refresh rotation, and logout revocation.

#### 13. Dependencies
Database (`users`), Redis (Token blacklist), Email Dispatcher.

#### 14. Future Extension Points
Social Login (Apple / Google OAuth), Passkeys / Biometric WebAuthn, Multi-Factor Authentication (SMS/TOTP).

---

### Module 2: User Profile (`PROF`)

#### 1. Objective
Maintain personal identity, preferences, avatar, and timezone settings per user.

#### 2. User Problem
Family members need to identify who completed chores, bought items, or paid bills.

#### 3. Actors
Authenticated User.

#### 4. User Stories
- **US-PROF-01**: As a user, I want to upload an avatar and set my display name so that my family members recognize my activity.
- **US-PROF-02**: As a user, I want to set my local timezone so that task deadlines and calendar events are displayed accurately.

#### 5. Functional Requirements
- **`PROF-001`**: The system MUST allow users to view and update display name, phone number, avatar URL, and timezone.
- **`PROF-002`**: The system MUST support direct avatar image uploads (JPEG/PNG/WebP, max 5MB).
- **`PROF-003`**: The system MUST detect the client browser/device timezone upon initial onboarding and set it as default.

#### 6. Business Rules
- Display name cannot be empty and is capped at 100 characters.
- Timezone must be a valid IANA Timezone string (e.g. `America/New_York`, `Asia/Kolkata`).

#### 7. Validation
- Image upload MIME type must be strictly checked (`image/jpeg`, `image/png`, `image/webp`).

#### 8. Permissions
`current_user` can only update their own profile (`user_id = token.user_id`).

#### 9. Notifications
None.

#### 10. UI States
- **Empty State**: Displays placeholder initials avatar when no photo is uploaded.
- **Loading State**: Skeleton loading for profile fields.
- **Error State**: Toast notification if image upload fails.

#### 11. Edge Cases
- User changes timezone: All relative timestamps on client adapt immediately without corrupting stored UTC database values.

#### 12. Acceptance Criteria
- Profile updates persist and reflect in Home member lists within 1 second.

#### 13. Dependencies
`AUTH`, Storage Service (S3 / Cloud Storage).

#### 14. Future Extension Points
Personal quiet hours schedule, theme preferences, language localizations.

---

### Module 3: Home Creation & Context (`HOME`)

#### 1. Objective
Establish the Home as the primary multi-tenant root workspace and enable multi-home switching.

#### 2. User Problem
Users need a shared household workspace that isolates their family's data from others.

#### 3. Actors
Authenticated User, Home Owner, Home Admin.

#### 4. User Stories
- **US-HOME-01**: As a user, I want to create a new Home workspace with my currency and timezone so that my household has a dedicated space.
- **US-HOME-02**: As a user managing multiple homes, I want to switch between homes from a top-bar dropdown so that I can check on my cabin or parents' home.

#### 5. Functional Requirements
- **`HOME-001`**: The system MUST create a `Home` record and automatically assign the creator the `OWNER` role in `home_members`.
- **`HOME-002`**: The system MUST initialize default categories and a default "Weekly Groceries" list upon Home creation.
- **`HOME-003`**: The system MUST allow Home Admins and Owners to update Home Name, Avatar, Currency, and Address.
- **`HOME-004`**: The system MUST provide a Home Switcher endpoint returning all active homes for the current user.
- **`HOME-005`**: Only the `OWNER` role MUST be permitted to delete or archive a Home workspace.

#### 6. Business Rules
- A Free Tier user can own at most 1 Home workspace.
- Currency must be an ISO 4217 standard 3-letter code.
- Deleting a home triggers a soft-delete grace period of 30 days before permanent deletion.

#### 7. Validation
- Home name must be between 2 and 120 characters.

#### 8. Permissions
- Creation: Any authenticated user within tier limits.
- Editing: `home:edit` (`OWNER`, `ADMIN`).
- Deletion: `home:delete` (`OWNER` only).

#### 9. Notifications
In-app toast upon creation; confirmation email upon deletion request.

#### 10. UI States
- **Empty State (No Homes)**: Onboarding modal: "Welcome to Ozhzo Verse! Create your first Home or join with an invite code."
- **Loading State**: Shimmer cards for home overview.
- **Error State**: "Failed to load home settings. Please retry."

#### 11. Edge Cases
- User belongs to multiple homes and active home is deleted: Client automatically defaults to next available active home.

#### 12. Acceptance Criteria
- Automated test verifies compound foreign key cascade and query scoping by `home_id`.

#### 13. Dependencies
`AUTH`, `PROF`, `SUB`.

#### 14. Future Extension Points
Home address geocoding, multi-home summary dashboard.

---

### Module 4: Home Members & Invitations (`MEM`)

#### 1. Objective
Enable seamless onboarding of family members and roommates into a shared Home workspace.

#### 2. User Problem
Users struggle to get family members onto new apps without tedious setup.

#### 3. Actors
Home Owner, Home Admin, Invitee, Active Member.

#### 4. User Stories
- **US-MEM-01**: As a Home Admin, I want to send an invite link to my partner so they can join our home with 1 click.
- **US-MEM-02**: As an invitee, I want to preview the home details before accepting the invitation.
- **US-MEM-03**: As a Home Owner, I want to remove a former roommate so they no longer have access to our home data.

#### 5. Functional Requirements
- **`MEM-001`**: The system MUST generate secure, 64-character high-entropy invite tokens with a 7-day expiration.
- **`MEM-002`**: The system MUST support role designation (`ADMIN`, `MEMBER`, `CHILD`, `GUEST`) upon invite creation.
- **`MEM-003`**: The system MUST allow invitees to accept tokens and automatically attach to the target Home with the designated role.
- **`MEM-004`**: The system MUST allow Owners/Admins to view member rosters and revoke pending invites.
- **`MEM-005`**: The system MUST allow Owners/Admins to remove non-owner members.

#### 6. Business Rules
- Free Tier homes are capped at 5 active members.
- An invite token can only be accepted once (`status = 'ACCEPTED'`).
- The Home Owner cannot be removed or demoted by an Admin.

#### 7. Validation
- Invite role must be a valid enum (`ADMIN`, `MEMBER`, `CHILD`, `GUEST`).

#### 8. Permissions
- Invite creation / Member removal: `members:invite`, `members:remove` (`OWNER`, `ADMIN`).

#### 9. Notifications
- Outbound invitation email to recipient.
- In-app notification to Owner/Admins when a member joins.

#### 10. UI States
- **Empty State (Only Owner)**: "You're the only member here. Invite your family or roommates to get started!"
- **Loading State**: Avatar skeleton loaders in Member list.
- **Error State**: "This invitation has expired or has already been used."

#### 11. Edge Cases
- User invited via email registers with a different email: Token verification allows binding to authenticated user upon explicit confirmation.

#### 12. Acceptance Criteria
- Integration test asserts that revoked or expired tokens return HTTP 410 Gone.

#### 13. Dependencies
`AUTH`, `HOME`, `NOTIF`.

#### 14. Future Extension Points
QR Code invite scanning, temporary guest expiration timers.

---

### Module 5: Roles & Permissions (`RBAC`)

#### 1. Objective
Enforce home-scoped role-based access control across all API endpoints and UI views.

#### 2. User Problem
Households need role distinctions so children don't see financial bills and guests don't alter home settings.

#### 3. Actors
Owner, Admin, Adult Member, Child, Guest.

#### 4. User Stories
- **US-RBAC-01**: As a parent, I want to assign my teenager the "Child" role so they can see their chores without accessing our utility bills.
- **US-RBAC-02**: As an Admin, I want to manage chores and groceries without having access to the Owner's credit card billing.

#### 5. Functional Requirements
- **`RBAC-001`**: The system MUST evaluate permissions dynamically against `(user_id, active_home_id)`.
- **`RBAC-002`**: The system MUST enforce the following hierarchy: `OWNER > ADMIN > MEMBER > CHILD > GUEST`.
- **`RBAC-003`**: The system MUST reject unauthorized actions with HTTP 403 Forbidden and standard error payload.
- **`RBAC-004`**: The system MUST filter sensitive endpoints (e.g. `/bills`) entirely out of responses for `CHILD` and `GUEST` roles.

#### 6. Business Rules
- Roles are strictly scoped to `home_id`; global super-roles do not exist in the domain layer.
- Owners cannot be demoted; ownership transfer is an explicit, verified two-step handshake.

#### 7. Validation
- Role modifications must validate that the caller's role is strictly higher than the target role.

#### 8. Permissions
Policy Guard Dependencies in FastAPI.

#### 9. Notifications
Notification dispatched to member when their role is adjusted by an Admin.

#### 10. UI States
- Unauthorized UI elements (e.g., Delete Home button) are hidden from unauthorized roles.

#### 11. Edge Cases
- User role changed mid-session: Next API request re-evaluates role from Redis/DB immediately.

#### 12. Acceptance Criteria
- Security test suite asserts 100% rejection on unauthorized endpoint calls across all 5 roles.

#### 13. Dependencies
`AUTH`, `HOME`, `MEM`.

#### 14. Future Extension Points
Custom permission overrides, granular room-level permissions.

---

### Module 6: Home Dashboard (`DASH`)

#### 1. Objective
Deliver a unified, single-screen morning pulse of household chores, low stock items, bills, and schedule.

#### 2. User Problem
Family members have to check multiple disparate tools to know what needs attention today.

#### 3. Actors
All Home Members.

#### 4. User Stories
- **US-DASH-01**: As a user opening the app in the morning, I want to see everything due today in one glance so I can plan my day.
- **US-DASH-02**: As a family member, I want to see a live activity feed so I know what has already been done today.

#### 5. Functional Requirements
- **`DASH-001`**: The system MUST provide an aggregated endpoint (`GET /api/v1/homes/{home_id}/dashboard`) returning:
  - Tasks due today / overdue.
  - Low stock & expiring inventory items.
  - Pending shopping list item count.
  - Upcoming bills (next 7 days).
  - Today's calendar events.
  - Recent activity stream (last 20 items).
- **`DASH-002`**: Response MUST adapt dynamically based on user role (hiding bills from Child/Guest).
- **`DASH-003`**: Dashboard load time MUST NOT exceed 300ms under standard network conditions.

#### 6. Business Rules
- Completed chores remain visible in the dashboard's "Done Today" section until midnight home timezone.

#### 7. Validation
- Valid `home_id` header or path parameter required.

#### 8. Permissions
`dashboard:view` (all active members).

#### 9. Notifications
None.

#### 10. UI States
- **Empty State**: "All caught up! No chores due or bills pending for today."
- **Loading State**: Unified skeleton layout with card placeholders.
- **Error State**: "Unable to load household dashboard. Pull down to refresh."

#### 11. Edge Cases
- Timezone shifts across midnight: Client queries with explicit date bounds to prevent off-by-one errors.

#### 12. Acceptance Criteria
- Single database transaction or optimized parallel queries resolve dashboard payload in $<300$ms.

#### 13. Dependencies
`TASK`, `INV`, `SHOP`, `BILL`, `EVENT`.

#### 14. Future Extension Points
Weather widget, customizable widget order, household streak highlights.

---

### Module 7: Household Inventory (`INV`)

#### 1. Objective
Track household pantry, fridge, cleaning, and medical supplies with threshold alerts and expiry dates.

#### 2. User Problem
Households frequently buy duplicate groceries or discover expired items in the back of the pantry.

#### 3. Actors
Home Owner, Home Admin, Adult Member.

#### 4. User Stories
- **US-INV-01**: As a home cook, I want to track fridge and pantry supplies with minimum thresholds so I get alerted before running out.
- **US-INV-02**: As a parent, I want to log expiry dates for medicine and dairy so we don't consume expired goods.
- **US-INV-03**: As a user, I want to tap "Add to Shopping List" on a low item so I don't forget to buy it.

#### 5. Functional Requirements
- **`INV-001`**: The system MUST allow categorized item creation (Pantry, Fridge, Freezer, Cleaning, Medicine).
- **`INV-002`**: The system MUST track Name, Category, Quantity, Unit (pcs, kg, L, boxes), Min Threshold, and Expiry Date.
- **`INV-003`**: The system MUST dynamically evaluate status: `IN_STOCK`, `LOW_STOCK` ($qty \le threshold$), `OUT_OF_STOCK` ($qty = 0$), `EXPIRED` ($expiry < today$).
- **`INV-004`**: The system MUST provide an instant "+ Add to Shopping List" action on any inventory item.
- **`INV-005`**: The system MUST support quick inline quantity increments (`+` / `-`).

#### 6. Business Rules
- Quantity cannot be negative.
- Threshold defaults to 1 if unspecified.

#### 7. Validation
- Item name must be between 1 and 120 characters.
- Expiry date must be a valid ISO 8601 date string (`YYYY-MM-DD`).

#### 8. Permissions
- View: `inventory:view` (`OWNER`, `ADMIN`, `MEMBER`).
- Create/Edit: `inventory:create`, `inventory:edit` (`OWNER`, `ADMIN`, `MEMBER`).
- Delete: `inventory:delete` (`OWNER`, `ADMIN`).

#### 9. Notifications
In-app alert when item transitions to `LOW_STOCK` or reaches 3 days before expiry.

#### 10. UI States
- **Empty State**: "Your inventory is empty. Add your first 5 essential pantry items!"
- **Loading State**: Grid shimmer cards.
- **Error State**: Inline error toast on failed update.

#### 11. Edge Cases
- Fractional quantities (e.g. 0.5 kg): Handled as `NUMERIC(10,2)`.

#### 12. Acceptance Criteria
- Decrementing stock below threshold immediately reflects as "Low Stock" across all active clients.

#### 13. Dependencies
`HOME`, `SHOP`.

#### 14. Future Extension Points
Barcode scanning, receipt OCR, recipe-to-inventory deduction.

---

### Module 8: Shopping Lists (`SHOP`)

#### 1. Objective
Provide real-time collaborative grocery and shopping checklists with live in-store synchronization.

#### 2. User Problem
Family members buy duplicate items or text fragmented grocery lists back and forth.

#### 3. Actors
All Household Members.

#### 4. User Stories
- **US-SHOP-01**: As a family member at the supermarket, I want to check off items in real time so my partner at home sees what is already bought.
- **US-SHOP-02**: As a shopper, I want checking off milk to prompt me to update our fridge inventory to "In Stock".
- **US-SHOP-03**: As a user, I want multiple lists (e.g., "Weekly Groceries", "Hardware Store") to keep items organized.

#### 5. Functional Requirements
- **`SHOP-001`**: The system MUST support multiple shopping lists per home with a default primary list.
- **`SHOP-002`**: The system MUST support adding, editing, checking, and deleting items with Name, Quantity, Unit, and Category.
- **`SHOP-003`**: The system MUST broadcast check/uncheck events in real time (<1s) via Redis Pub/Sub to all connected clients.
- **`SHOP-004`**: The system MUST record `checked_by` and `checked_at` metadata for checked items.
- **`SHOP-005`**: When an item linked to an `inventory_item_id` is checked, the system MUST prompt the user to automatically restock the inventory.

#### 6. Business Rules
- Checked items are visually struck through and moved to the bottom "Completed" section.
- "Clear Completed" archives checked items without deleting historical audit records.

#### 7. Validation
- Item name cannot be blank.

#### 8. Permissions
- View/Check: `shopping:view`, `shopping:check` (All roles).
- Create/Edit: `shopping:create`, `shopping:edit` (`OWNER`, `ADMIN`, `MEMBER`).
- Delete List: `shopping:delete` (`OWNER`, `ADMIN`).

#### 9. Notifications
Real-time shopping sync events via WebSockets/SSE.

#### 10. UI States
- **Empty State**: "Shopping list is clear! Add items manually or from your low inventory."
- **Loading State**: Item list skeleton.
- **Error State**: "Sync disconnected. Retrying connection..."

#### 11. Edge Cases
- Two members check different items simultaneously in the store: Optimistic UI updates with last-write-wins at item granularity prevent race conditions.

#### 12. Acceptance Criteria
- Live sync delivers item check events across devices within 1 second.

#### 13. Dependencies
`HOME`, `INV`, Redis.

#### 14. Future Extension Points
Aisle auto-sorting, supermarket route optimization, grocery price estimation.

---

### Module 9: Tasks & Household Responsibilities (`TASK`)

#### 1. Objective
Provide a unified household coordination engine to answer "WHAT NEEDS TO BE DONE FOR OUR HOME?", track domestic chores, manage maintenance schedules, and preserve completion history.

#### 2. User Problem
Household tasks (cleaning, maintenance, bills, appliance servicing) are forgotten, uncoordinated, or lack clear assignment and historical maintenance records.

#### 3. Actors
All Household Members (`HOME_ADMIN`, `MEMBER`, `CHILD`, `GUEST`).

#### 4. User Stories
- **US-TASK-01**: As a home member, I want to quickly add a household task with just a title so that I don't get slowed down by complex forms.
- **US-TASK-02**: As a parent, I want to set up recurring chores (e.g. *Clean water filter every 30 days*, *AC Service every 6 months*) so the system schedules them automatically upon completion.
- **US-TASK-03**: As a family member, I want to see "My Tasks" and "Due Today" so I know what responsibilities I have for the day.
- **US-TASK-04**: As a homeowner, I want to view the completed task history to verify when appliances were last serviced and by whom.

#### 5. Functional Requirements
- **`TASK-001`**: The system MUST support Quick Add requiring only Title (min 2 chars). Priority defaults to `NORMAL`.
- **`TASK-002`**: Optional task fields MUST include `description`, `priority` (`LOW`, `NORMAL`, `HIGH`, `URGENT`), `assigned_to`, `due_date`, `category_id`, `template_id`, `recurrence_type`, `recurrence_interval_days`, and `recurrence_strategy`.
- **`TASK-003`**: The system MUST support recurrence strategies: `SCHEDULED_DATE` (fixed calendar schedule) and `COMPLETION_DATE` (service rhythm calculated from actual completion date).
- **`TASK-004`**: Completing a recurring task MUST mark the current instance `COMPLETED` (capturing `completed_by` and `completed_at`) and atomically spawn the next instance.
- **`TASK-005`**: The system MUST dynamically derive time states: `OVERDUE` ($\text{due\_date} < \text{today}$), `DUE_TODAY` ($\text{due\_date} == \text{today}$), `UPCOMING` ($\text{due\_date} > \text{today}$), and `NO_DUE_DATE`.
- **`TASK-006`**: Completed tasks MUST be preserved in an immutable, searchable Task Completion History.

#### 6. Business Rules
- Tasks belong to the Home, not individual users.
- Assignment is optional; unassigned tasks remain visible on the shared Home Board.
- Client cannot spoof `created_by` or `completed_by`; resolved server-side.

#### 7. Validation
- Title must be between 2 and 200 characters.

#### 8. Permissions
- View: `tasks:view` (All active members).
- Create/Edit/Assign/Complete: `tasks:create`, `tasks:edit`, `tasks:complete` (`HOME_ADMIN`, `MEMBER`, `CHILD`).
- Delete: `tasks:delete` (`HOME_ADMIN`, `MEMBER`).

#### 9. Notifications
- Real-time SSE / WebSocket update dispatched to family devices on task creation, assignment, and completion.

#### 10. UI States
- **Empty State**: "No tasks pending for our home! Everything is clean and up to date."
- **Loading State**: Shimmer cards.
- **Error State**: Non-blocking toast alerts.

#### 11. Acceptance Criteria
- Quick Add creates a task in $< 100\text{ms}$.
- Completing a 30-day recurring task spawns the next occurrence scheduled exactly 30 days from completion.
- Cross-home task queries return HTTP 403 Forbidden.

#### 12. Dependencies
`HOME`, `MEM`, `AUTH`.

#### 14. Future Extension Points
Gamified points/rewards system, chore rotation engine, photo proof of completion.

---

### Module 10: Bills & Recurring Household Expenses (`BILL`)

#### 1. Objective
Provide a unified household financial obligation ledger tracking recurring domestic utilities, subscriptions, rent, and maintenance expenses, with variable invoice support, partial payments, and permanent payment ledgers.

#### 2. User Problem
Households miss utility due dates, lose track of variable electricity/water costs, or double-pay bills because there is no shared visibility into what is due, who is responsible, and whether it was already paid.

#### 3. Actors
Home Owner, Home Admin, Home Member.

#### 4. User Stories
- **US-BILL-01**: As a family member, I want to see all upcoming and overdue bills for our home so we never incur late fees.
- **US-BILL-02**: As the responsible member for utilities, I want to record the actual amount paid for variable electricity/water bills while preserving the expected baseline.
- **US-BILL-03**: As a payer, I want to record partial payments (e.g. paying tuition in installments) with transparent remaining balance tracking.
- **US-BILL-04**: As a household, we want an immutable payment history ledger to verify past settlements.

#### 5. Functional Requirements
- **`BILL-001`**: The system MUST allow creating bills with `title`, `expected_amount`, `currency`, `due_date`, `recurrence_type` (`NONE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `YEARLY`, `CUSTOM_DAYS`), `recurrence_strategy` (`SCHEDULED_DATE`, `PAYMENT_DATE`), and `responsible_member_id`.
- **`BILL-002`**: The system MUST track status: `UNPAID`, `PARTIALLY_PAID`, `PAID`, `CANCELLED`, and derive `OVERDUE` and `DUE_TODAY`.
- **`BILL-003`**: The system MUST record payment settlements with `paid_by`, `amount_paid`, `paid_date`, `payment_method` (`CASH`, `BANK_TRANSFER`, `UPI`, `CARD`, `ONLINE`, `OTHER`), and `notes`.
- **`BILL-004`**: For recurring bills, reaching full payment MUST atomically advance the recurring cycle and spawn the next occurrence.
- **`BILL-005`**: The system MUST preserve both the expected amount and actual payment transaction records.

#### 6. Business Rules
- Monetary amounts must be strictly stored and calculated as `NUMERIC(12,2)` / Python `Decimal`.
- Payment history in `bill_payments` is an append-only immutable ledger.
- Responsible member and payer must be active members of the same Home.

#### 7. Validation
- Expected amount and payment amount must be positive decimals $> 0.00$.

#### 8. Permissions
- View: `bills:view` (All active members).
- Create / Edit: `bills:create`, `bills:edit` (`HOME_ADMIN`, `MEMBER`).
- Pay: `bills:pay` (`HOME_ADMIN`, `MEMBER`).
- Delete: `bills:delete` (`HOME_ADMIN`).

#### 9. UI States
- **Empty State**: "No active bills for our home! All household expenses are settled."
- **Loading State**: Shimmer financial KPI cards.
- **Error State**: Non-blocking toast alerts.

#### 10. Acceptance Criteria
- Quick Add creates a bill in $< 100\text{ms}$.
- Recording variable utility payment (e.g. ₹2,137 vs expected ₹2,000) preserves both values.
- Partial payment (₹6,000 on ₹10,000 bill) updates status to `PARTIALLY_PAID` with balance ₹4,000.
- Cross-home bill operations return HTTP 403 Forbidden.

#### 8. Permissions
- View/Pay: `bills:view`, `bills:pay` (`OWNER`, `ADMIN`, `MEMBER`).
- Create/Edit/Delete: `bills:create`, `bills:edit`, `bills:delete` (`OWNER`, `ADMIN`).
- Strictly forbidden for `CHILD` and `GUEST`.

#### 9. Notifications
- Push and In-app alert at T-3 days before due date.
- Morning push alert on the exact due date.

#### 10. UI States
- **Empty State**: "No bills logged. Add utilities, rent, or internet bills to stay on top of expenses."
- **Loading State**: Table row skeletons.
- **Error State**: "Failed to record bill payment."

#### 11. Edge Cases
- Partial bill payments: Records payment amount against bill ledger while maintaining residual balance or marking settled.

#### 12. Acceptance Criteria
- Daily cron worker identifies bills due in 3 days and generates notifications without duplicate dispatches.

#### 13. Dependencies
`HOME`, `MEM`, `NOTIF`.

#### 14. Future Extension Points
Bill splitting calculator, receipt photo attachment, bank feed integration.

---

### Module 11: Calendar & Events (`EVENT`)

#### 1. Objective
Provide a unified shared calendar for household milestones, maintenance visits, and family appointments.

#### 2. User Problem
Family members schedule clashing events or forget domestic appointments (e.g. plumber visits).

#### 3. Actors
All Household Members.

#### 4. User Stories
- **US-EVENT-01**: As a user, I want to schedule a family event or maintenance visit on the shared calendar so everyone is informed.
- **US-EVENT-02**: As a member, I want to RSVP to a family dinner so the organizer knows who is attending.

#### 5. Functional Requirements
- **`EVENT-001`**: The system MUST support event creation with Title, Description, Start Time, End Time, All-Day flag, and Category.
- **`EVENT-002`**: The system MUST render Month and Week calendar views.
- **`EVENT-003`**: The system MUST display chore deadlines and bill due dates alongside calendar events.
- **`EVENT-004`**: The system MUST support member RSVP tracking (`ATTENDING`, `DECLINED`, `MAYBE`).

#### 6. Business Rules
- End time must be equal to or greater than start time.
- Events are stored in UTC in the database and converted to Home Timezone on client render.

#### 7. Validation
- Title must be between 2 and 160 characters.

#### 8. Permissions
- View: `calendar:view` (All roles).
- Create/Edit: `calendar:create`, `calendar:edit` (`OWNER`, `ADMIN`, `MEMBER`).
- RSVP: `calendar:rsvp` (All roles).
- Delete: `calendar:delete` (`OWNER`, `ADMIN`).

#### 9. Notifications
- Event invite notification dispatched to household members.
- Event reminder 1 hour before start time.

#### 10. UI States
- **Empty State (Day View)**: "No events scheduled for this day."
- **Loading State**: Calendar grid shimmer.
- **Error State**: "Failed to load calendar events."

#### 11. Edge Cases
- Daylight saving time transitions: Handled natively via Python `zoneinfo` and UTC ISO 8601 strings.

#### 12. Acceptance Criteria
- Events created by one member render on all family members' calendars immediately.

#### 13. Dependencies
`HOME`, `MEM`, `NOTIF`.

#### 14. Future Extension Points
External Google/Apple Calendar two-way sync, `.ics` feed subscription.

---

### Module 12: Notifications (`NOTIF`)

#### 1. Objective
Deliver timely, actionable, and non-intrusive domestic alerts across in-app, mobile push, and email channels.

#### 2. User Problem
Users miss important assignments, bill due dates, and grocery requests when not actively looking at the app.

#### 3. Actors
All Household Members.

#### 4. User Stories
- **US-NOTIF-01**: As a user, I want an in-app notification inbox so I can review all alerts in one place.
- **US-NOTIF-02**: As a mobile user, I want push notifications for urgent chore assignments and bill due dates.

#### 5. Functional Requirements
- **`NOTIF-001`**: The system MUST provide an in-app notification center with read/unread tracking and badge count.
- **`NOTIF-002`**: The system MUST support mobile push notifications via APNs and FCM for high-priority alerts.
- **`NOTIF-003`**: The system MUST support deep-linking from notifications directly to the target item (chore, bill, list).
- **`NOTIF-004`**: The system MUST provide "Mark as Read" and "Mark All as Read" endpoints.

#### 6. Business Rules
- Notifications are pruned automatically after 30 days.
- Quiet hours (if set) suppress mobile push alerts until morning.

#### 7. Validation
- Notification type must be a valid enum (`TASK_DUE`, `BILL_REMINDER`, `INVENTORY_EXPIRY`, `HOME_INVITE`).

#### 8. Permissions
Users can only view and mutate their own notifications (`user_id = token.user_id`).

#### 9. Notifications
In-App Inbox, APNs, FCM, Transactional Email.

#### 10. UI States
- **Empty State**: "You're all caught up! No unread notifications."
- **Loading State**: Notification item skeletons.
- **Error State**: "Unable to load notifications."

#### 11. Edge Cases
- Target entity deleted before user clicks notification: App displays toast: *"This item is no longer available."*

#### 12. Acceptance Criteria
- Dispatching a task assignment generates an in-app notification and decrements the unread count upon reading.

#### 13. Dependencies
`AUTH`, `HOME`, Push Service (APNs/FCM).

#### 14. Future Extension Points
Notification channel granularity settings, daily morning digest email.

---

### Module 13: Dynamic Subscription & Pricing Management (`SUB`)

#### 1. Objective
Provide a fully dynamic, data-driven subscription, regional pricing, first-class coupon management, promotional campaigns, direct administrative grants, and member seat allocation architecture configurable entirely by `SUPER_ADMIN` with zero hardcoded financial rules.

#### 2. User Problem
Commercial tariffs, introductory durations, seat prices, percentage/fixed coupons, free durations (1m, 3m, 6m, 1y), regional currencies, and direct entitlements vary across markets and evolve over time without requiring software redeployment.

#### 3. Actors
Super Admin (System), Home Owner (Household Custodian), System Calculation Engine.

#### 4. User Stories
- **US-SUB-01**: As a Super Admin, I want to configure regional plans, standard list prices, first-class coupons, marketing campaigns, direct subscription grants, and feature entitlements dynamically.
- **US-SUB-02**: As a Home Owner, I want transparent visibility into my introductory period, covered member seats, and authoritative coupon quotes before checkout.
- **US-SUB-03**: As a subscriber, I want historical price locking so my existing plan rate is preserved when platform tariffs change.
- **US-SUB-04**: As an invited member, I want to apply promotional vouchers/coupons upon invitation acceptance with anti-double-benefit protection.

#### 5. Functional Requirements
- **`SUB-001`**: The system MUST store plans, regional standard prices, campaigns, coupons, coupon redemptions, direct grants, and feature entitlements in normalized database tables.
- **`SUB-002`**: The system MUST perform authoritative price calculations on the backend (`POST /api/v1/subscription/calculate`) incorporating standard prices, seat totals, percentage/fixed discounts, and free period duration entitlements.
- **`SUB-003`**: The system MUST support dynamic free duration coupons (1m, 3m, 6m, 1y) generating active subscriptions with zero payment required and transitioning to `RENEWAL_REQUIRED` upon expiry.
- **`SUB-004`**: The system MUST support direct Super Admin grants without a coupon code, writing immutable audit records to `subscription_grants` and `subscription_audit_logs`.
- **`SUB-005`**: The system MUST enforce Super Admin role authorization (`is_super_admin: true`) for all coupon, campaign, grant, pricing, and plan modifications.
- **`SUB-006`**: The system MUST preserve historical pricing and completed redemptions through immutable snapshot records.

#### 6. Business Rules
- Pricing, coupons, campaigns, and seat limits are 100% data-driven; no hardcoded prices or user limits exist in frontend or server business logic.
- Non-super-admins cannot access administrative pricing routes (`HTTP 403 Forbidden`).
- Coupon stacking is disabled by default; only one discount/benefit applies per checkout.

#### 7. Validation
- Hierarchical validation: code status, active date range, total redemption limit, per-user limit, per-home limit, user/home eligibility, and geographic restrictions (Country, State, District, Postal Code).

#### 8. Permissions
- `admin:plans:*`, `admin:prices:*`, `admin:features:*` (`SUPER_ADMIN` only).
- `subscription:view` (`OWNER`, `ADMIN`).
- `subscription:manage` (`OWNER` only).

#### 9. Notifications
- Promotional period expiration warning alerts dispatched at 30 days and 7 days prior to renewal.

#### 10. UI States
- **Introductory Active**: Shows active trial badge with days remaining and dynamic per-seat rate for additional members.
- **Seat Allocation**: Interactive seat adjuster rendering authoritative dynamic backend totals.

#### 11. Edge Cases
- Regional fallback: When a country has no specific price configuration, the system automatically falls back to `GLOBAL` regional pricing.

### Module 14: System Administration & Platform Governance (`ADMIN`)

#### 1. Objective
Provide a dedicated, isolated platform administration capability for `SUPER_ADMIN` and system operators to search/manage users, inspect/suspend household workspaces, configure global flags, monitor telemetry, and review immutable audit logs.

#### 2. User Problem
Platform operators need tools to govern platform health, resolve customer disputes, suspend fraudulent accounts, configure tariffs/promotions, and audit administrative actions without accessing or contaminating household-specific domestic operations.

#### 3. Actors
Super Admin, Platform Admin, Support Admin, System Security Auditor.

#### 4. User Stories
- **US-ADMIN-01**: As a Super Admin, I want to search and inspect platform users, their status, and their home memberships.
- **US-ADMIN-02**: As a Super Admin, I want to suspend or reactivate users and household workspaces with an explicit audit reason.
- **US-ADMIN-03**: As a Security Auditor, I want an immutable audit trail of all platform-level administrative mutations.
- **US-ADMIN-04**: As a Platform Operator, I want high-level telemetry and foundation analytics on platform growth and subscription health.

#### 5. Functional Requirements
- **`ADMIN-001`**: The system MUST provide dedicated `/api/v1/admin/*` routes strictly guarded by system-level authorization (`is_super_admin: true`).
- **`ADMIN-002`**: The system MUST reject non-super-admins (including Home Admins and Owners) with `HTTP 403 Forbidden`.
- **`ADMIN-003`**: The system MUST support user management (search, detail, suspend, reactivate) and home management (search, detail, suspend, reactivate).
- **`ADMIN-004`**: The system MUST log all administrative mutations into `subscription_audit_logs` storing actor, action, old/new states, and reason.
- **`ADMIN-005`**: The system MUST provide aggregate foundation analytics (total/active users, total/active homes, active subscriptions).

---

## 3. Comprehensive Traceability Matrix

| Requirement ID | User Story | API Endpoint | Database Entity | UI Screen / Component | Test Case ID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`AUTH-001`** | `US-AUTH-01` | `POST /api/v1/auth/register` | `users`, `user_profiles` | `RegisterScreen` | `TC-AUTH-01` |
| **`AUTH-002`** | `US-AUTH-02` | `POST /api/v1/auth/login` | `users` | `LoginScreen` | `TC-AUTH-02` |
| **`AUTH-003`** | `US-AUTH-02` | `POST /api/v1/auth/refresh` | `users` | `AuthInterceptor` | `TC-AUTH-03` |
| **`AUTH-004`** | `US-AUTH-03` | `POST /api/v1/auth/forgot-password` | `users` | `ForgotPasswordScreen`| `TC-AUTH-04` |
| **`PROF-001`** | `US-PROF-01` | `PATCH /api/v1/users/me` | `user_profiles` | `ProfileSettingsModal`| `TC-PROF-01` |
| **`HOME-001`** | `US-HOME-01` | `POST /api/v1/homes` | `homes`, `home_members` | `CreateHomeModal` | `TC-HOME-01` |
| **`HOME-002`** | `US-HOME-02` | `GET /api/v1/homes` | `homes`, `home_members` | `HomeSwitcherDropdown`| `TC-HOME-02` |
| **`MEM-001`** | `US-MEM-01` | `POST /api/v1/homes/{id}/invites` | `home_invites` | `InviteMemberDialog` | `TC-MEM-01` |
| **`MEM-003`** | `US-MEM-02` | `POST /api/v1/homes/invites/{token}/accept`| `home_members`, `home_invites` | `AcceptInviteScreen` | `TC-MEM-02` |
| **`MEM-005`** | `US-MEM-03` | `DELETE /api/v1/homes/{id}/members/{uid}` | `home_members` | `MemberListTab` | `TC-MEM-03` |
| **`RBAC-001`** | `US-RBAC-01` | `GET /api/v1/homes/{id}/bills` | `home_members` | `PermissionGuard` | `TC-RBAC-01` |
| **`DASH-001`** | `US-DASH-01` | `GET /api/v1/homes/{id}/dashboard` | Aggregated Views | `HomeDashboardScreen` | `TC-DASH-01` |
| **`INV-001`** | `US-INV-01` | `POST /api/v1/homes/{id}/inventory/items` | `inventory_items` | `AddInventoryModal` | `TC-INV-01` |
| **`INV-003`** | `US-INV-01` | `PATCH /api/v1/homes/{id}/inventory/items/{id}`| `inventory_items` | `InventoryItemCard` | `TC-INV-02` |
| **`INV-004`** | `US-INV-03` | `POST /api/v1/homes/{id}/inventory/items/{id}/add-to-shopping`| `shopping_list_items` | `QuickAddButton` | `TC-INV-03` |
| **`SHOP-001`** | `US-SHOP-01` | `PATCH /api/v1/homes/{id}/shopping-lists/items/{id}`| `shopping_list_items` | `ShoppingListTile` | `TC-SHOP-01` |
| **`TASK-001`** | `US-TASK-01` | `POST /api/v1/homes/{id}/tasks` | `tasks` | `CreateTaskModal` | `TC-TASK-01` |
| **`TASK-004`** | `US-TASK-01` | `POST /api/v1/homes/{id}/tasks/{id}/complete` | `tasks`, `task_activity` | `TaskCheckbox` | `TC-TASK-02` |
| **`BILL-001`** | `US-BILL-01` | `POST /api/v1/homes/{id}/bills` | `bills` | `CreateBillModal` | `TC-BILL-01` |
| **`BILL-003`** | `US-BILL-03` | `POST /api/v1/homes/{id}/bills/{id}/pay` | `bills`, `bill_payments`| `PayBillDialog` | `TC-BILL-02` |
| **`EVENT-001`**| `US-EVENT-01`| `POST /api/v1/homes/{id}/calendar/events` | `calendar_events` | `ScheduleEventModal` | `TC-EVENT-01`|
| **`NOTIF-001`**| `US-NOTIF-01`| `GET /api/v1/notifications` | `notifications` | `NotificationCenter` | `TC-NOTIF-01`|
| **`SUB-001`** | `US-SUB-01` | `GET /api/v1/homes/{id}/subscription` | `home_subscriptions` | `SubscriptionSettings`| `TC-SUB-01` |
| **`SUB-003`** | `US-SUB-01` | `POST /api/v1/homes/{id}/subscription/upgrade` | `home_subscriptions` | `StripeCheckoutModal` | `TC-SUB-02` |
