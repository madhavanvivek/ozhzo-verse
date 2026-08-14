# User Journeys & Operational Workflows — Ozhzo Verse

*Document Classification: Definitive Source of Truth*  
*Target Audience: Product Managers, Frontend/Mobile Engineers, QA Automation Engineers, UX Designers*

---

## 1. Journey 1: New User Registration

- **Actor**: Unregistered User (New Household Creator or Invited Member)
- **Preconditions**: User has internet access and an active email address.
- **Steps**:
  1. User navigates to the registration screen on Web or Mobile app.
  2. Enters Email, Full Name, Password (confirming password complexity rules), and accepts Terms of Service.
  3. Clicks "Create Account".
- **System Behaviour**:
  1. Validates email format and asserts uniqueness against the `users` table.
  2. Hashes password using Argon2id / bcrypt.
  3. Creates record in `users` and initializes `user_profiles` with display name and detected client timezone.
  4. Generates a secure verification token and dispatches a welcome verification email.
  5. Issues short-lived JWT access token and secure HTTP-only refresh token.
- **Success State**: Account created; user is authenticated and guided to the "Create or Join Home" onboarding fork.
- **Failure State**: Registration blocked if email already exists or password fails complexity criteria. Displays inline error: *"An account with this email already exists."*
- **Notifications**: Transactional welcome email with account verification link.
- **Edge Cases**:
  - Network disconnection during submission: Client retries gracefully with idempotent payload.
  - User attempts to register with disposable/temporary email: Blocked by backend domain validator.

---

## 2. Journey 2: User Login

- **Actor**: Registered User
- **Preconditions**: User has an existing, active account in Ozhzo Verse.
- **Steps**:
  1. User enters registered email and password on the Login screen.
  2. Taps "Sign In".
- **System Behaviour**:
  1. Backend looks up normalized email in `users` table.
  2. Verifies password hash against stored hash.
  3. Verifies account `is_active = TRUE`.
  4. Resolves user's associated Homes via `home_members` table.
  5. Generates JWT access token (15m) containing `user_id` and default active `home_id`.
  6. Sets rotating refresh token (30d) in secure HTTP-only cookie / mobile secure storage.
- **Success State**: User successfully authenticated and redirected to their most recently active Home Dashboard.
- **Failure State**: Returns 401 Unauthorized: *"Invalid email or password."* Account rate-limited after 5 consecutive failed attempts.
- **Notifications**: Security email alert if login occurs from a new device or unrecognized IP.
- **Edge Cases**:
  - User belongs to 0 homes: Redirected to Home Onboarding setup screen.
  - User's account is suspended: Returns 403 Forbidden with support contact link.

---

## 3. Journey 3: Create Home

- **Actor**: Authenticated User
- **Preconditions**: User is logged in and selects "Create New Home".
- **Steps**:
  1. User clicks "+ Create New Home" from onboarding or Home Switcher.
  2. Enters Home Name (e.g., "The Chen Residence"), selects Default Currency (USD, EUR, etc.), and sets Home Timezone.
  3. Clicks "Initialize Home".
- **System Behaviour**:
  1. Creates record in `homes` table with `created_by = current_user.id`.
  2. Creates entry in `home_members` table assigning `user_id = current_user.id`, `home_id = new_home.id`, `role = 'OWNER'`, `status = 'ACTIVE'`.
  3. Initializes default `inventory_categories` (Pantry, Fridge, Freezer, Cleaning, Medicine).
  4. Creates default "Weekly Groceries" record in `shopping_lists`.
  5. Initializes a `FREE` tier record in `home_subscriptions`.
- **Success State**: New Home workspace active; user is assigned `OWNER` role and lands on the empty-state Dashboard with guided setup cards.
- **Failure State**: Home creation fails if user exceeds maximum allowable homes under Free tier (1 Home limit). Prompts tier upgrade dialog.
- **Notifications**: In-app welcome toast: *"The Chen Residence is ready!"*
- **Edge Cases**:
  - Special characters / emojis in Home Name: Sanitized and safely stored as UTF-8.

---

## 4. Journey 4: Complete Home Profile & Settings

- **Actor**: Home Owner or Home Admin
- **Preconditions**: User is active in the Home context with `home:edit` permission.
- **Steps**:
  1. User navigates to Home Settings (`/homes/{home_id}/settings`).
  2. Uploads a Home cover image / avatar icon.
  3. Adds optional physical address or neighborhood area note.
  4. Adjusts default currency or timezone if needed.
  5. Clicks "Save Settings".
- **System Behaviour**:
  1. Validates image payload (max 5MB, JPEG/PNG/WebP).
  2. Stores image in S3/Cloud Storage and records URI in `homes.avatar_url`.
  3. Updates `homes` record and invalidates cached home metadata in Redis.
- **Success State**: Home profile updated; avatar reflects in navigation header across all family members' devices.
- **Failure State**: Returns 403 Forbidden if attempted by `MEMBER`, `CHILD`, or `GUEST`.
- **Notifications**: None.
- **Edge Cases**:
  - Image upload interrupted mid-flight: Client catches network error, cancels upload, and retains previous avatar.

---

## 5. Journey 5: Invite Family Member

- **Actor**: Home Owner or Home Admin
- **Preconditions**: User has `members:invite` permission and target home has not exceeded member limits.
- **Steps**:
  1. User opens "Members" settings and clicks "Invite Member".
  2. Selects intended role (`HOME ADMIN`, `ADULT MEMBER`, `CHILD`, `GUEST`).
  3. Optionally enters recipient's email or clicks "Generate Shareable Link".
  4. Clicks "Send Invite" or copies the secure invite URL.
- **System Behaviour**:
  1. Asserts home member count is below tier limit (e.g. Free Tier $\le 5$ members).
  2. Generates a 64-character high-entropy token stored in `home_invites` with `expires_at = NOW() + 7 days`.
  3. If email provided, dispatches branded invitation email containing the deep link.
- **Success State**: Invite link active; invite appears in "Pending Invites" list.
- **Failure State**: Blocked if member limit reached: *"Home has reached maximum member capacity. Upgrade to Premium to invite more family members."*
- **Notifications**: Outbound email to invitee: *"[Sender Name] invited you to join [Home Name] on Ozhzo Verse."*
- **Edge Cases**:
  - Inviting an email that is already an active member of this home: Backend rejects with *"User is already a member of this home."*

---

## 6. Journey 6: Accept Invitation

- **Actor**: Invitee (New or Existing User)
- **Preconditions**: Invitee has received a valid, unexpired invite link.
- **Steps**:
  1. Invitee clicks invite link (`https://app.ozhzoverse.com/invite?token=abc...`).
  2. App opens displaying Home preview: *"[Home Name] — Invited as [Role]"*.
  3. If logged in, clicks "Accept & Join". If not logged in, completes quick login/registration, which returns them to the accept screen.
- **System Behaviour**:
  1. Validates token exists in `home_invites` with `status = 'PENDING'` and `expires_at > NOW()`.
  2. Creates record in `home_members` (`home_id`, `user_id`, `role`, `status = 'ACTIVE'`).
  3. Updates `home_invites` record to `status = 'ACCEPTED'`.
  4. Invalidates user's cached home list in Redis.
  5. Sets active home to the newly joined home.
- **Success State**: User joined; redirected to Home Dashboard with contextual permissions active.
- **Failure State**: If token expired or revoked: Displays *"This invitation has expired or is no longer valid. Please request a new invite from the home owner."*
- **Notifications**: In-app notification and push alert sent to Home Owner/Admins: *"[Member Name] has joined [Home Name] as [Role]."*
- **Edge Cases**:
  - User accepts same invite link twice (concurrency race): Database transaction with row lock guarantees single acceptance.

---

## 7. Journey 7: View Home Dashboard

- **Actor**: Any Active Household Member (`OWNER`, `ADMIN`, `MEMBER`, `CHILD`, `GUEST`)
- **Preconditions**: User is authenticated with an active home selected.
- **Steps**:
  1. User opens app or navigates to `/dashboard`.
- **System Behaviour**:
  1. Client sends `GET /api/v1/homes/{home_id}/dashboard`.
  2. Backend evaluates user role:
     - For `OWNER`, `ADMIN`, `MEMBER`: Aggregates chores due today, low stock items, expiring items, upcoming bills (7d), today's calendar events, recent activity feed.
     - For `CHILD` / `GUEST`: Filters out bills and restricted items; returns only assigned chores, shopping list overview, and public events.
  3. Returns unified JSON payload in a single database roundtrip (<300ms).
- **Success State**: Cohesive dashboard renders with live summary tiles.
- **Failure State**: Network error displays offline cached state with banner: *"Viewing cached offline data. Reconnecting..."*
- **Notifications**: None.
- **Edge Cases**:
  - Completely empty home (new workspace): Renders friendly onboarding checklist with action prompts.

---

## 8. Journey 8: Add Inventory Item

- **Actor**: Home Owner, Home Admin, or Adult Member
- **Preconditions**: User has `inventory:create` permission.
- **Steps**:
  1. User navigates to Inventory module and clicks "+ Add Item".
  2. Enters Name ("Almond Milk"), Category ("Fridge"), Quantity (`2`), Unit (`liters`), Min Threshold (`1`), Expiry Date (`2026-08-25`).
  3. Clicks "Save Item".
- **System Behaviour**:
  1. Validates inputs (name required, quantity $\ge 0$).
  2. Inserts row into `inventory_items` table bound to `home_id`.
  3. Evaluates status: Since quantity (2) > threshold (1), sets `status = 'IN_STOCK'`.
- **Success State**: Item appears in the Fridge category list with green "In Stock" badge.
- **Failure State**: Validation error if quantity is negative or category missing.
- **Notifications**: None (or optional activity log entry).
- **Edge Cases**:
  - Duplicate item name added: Allowed (treated as separate batch with different expiry dates) or prompts user to merge quantities.

---

## 9. Journey 9: Inventory Becomes Low

- **Actor**: Any Adult Member updating stock OR Background Expiry Engine
- **Preconditions**: Item exists in household inventory.
- **Steps**:
  1. User in kitchen notices milk is almost finished; opens app and decrements quantity from `2` to `1` (or `0.5`).
- **System Behaviour**:
  1. Updates `quantity` in `inventory_items`.
  2. Evaluates invariant: `quantity <= min_threshold` (1.0).
  3. Transitions item `status` from `IN_STOCK` to `LOW_STOCK`.
  4. Triggers background notification event `INVENTORY_LOW_STOCK`.
- **Success State**: Item badge turns Amber ("Low Stock"); surfaces on Home Dashboard Low Stock alert card.
- **Failure State**: None.
- **Notifications**: In-app notification sent to household grocery shoppers: *"Almond Milk is running low in the Fridge."*
- **Edge Cases**:
  - Quantity set to 0: Status transitions immediately to `OUT_OF_STOCK` (Red badge).

---

## 10. Journey 10: Add Item to Shopping List

- **Actor**: Home Owner, Home Admin, or Adult Member
- **Preconditions**: User has `shopping:create` permission.
- **Steps**:
  1. User sees "Almond Milk" in Low Stock list on Dashboard or Inventory.
  2. Taps "+ Add to Shopping List" (or manually enters a custom item on the Shopping List screen).
  3. Selects target list ("Weekly Groceries") and quantity to buy (`2 liters`).
- **System Behaviour**:
  1. Inserts row into `shopping_list_items` referencing `inventory_item_id`.
  2. Broadcasts live sync update via Redis Pub/Sub to all connected household clients.
- **Success State**: Item appears in "Weekly Groceries" checklist with unchecked state.
- **Failure State**: Returns error if target shopping list was deleted.
- **Notifications**: Real-time badge update on Shopping List tab.
- **Edge Cases**:
  - Item already exists on the shopping list: Increments requested quantity rather than creating duplicate row.

---

## 11. Journey 11: Complete Shopping (In-Store Live Sync)

- **Actor**: Any Household Member at the Supermarket
- **Preconditions**: Active shopping list contains unchecked items.
- **Steps**:
  1. Member at store opens "Weekly Groceries" list.
  2. Puts Almond Milk in cart and taps the checkbox.
  3. Taps "Finish Shopping" when done.
- **System Behaviour**:
  1. Updates `shopping_list_items.is_checked = TRUE`, sets `checked_by = current_user.id`, `checked_at = NOW()`.
  2. Emits real-time event to other family members viewing the list (item strikes out instantly).
  3. If item was linked to inventory, displays modal prompt: *"Update Almond Milk in Fridge to In Stock (2 liters)?"*
  4. Upon confirmation, updates `inventory_items` quantity and resets status to `IN_STOCK`.
- **Success State**: Checked items cleared/archived; inventory stock levels automatically restored.
- **Failure State**: Offline mode queues check actions in local IndexedDB/SQLite and flushes when internet reconnects.
- **Notifications**: In-app activity feed logs: *"[Member Name] completed 8 items on Weekly Groceries."*
- **Edge Cases**:
  - Two members checking items at the same store simultaneously: Optimistic UI updates with last-write-wins at item level prevent lockups.

---

## 12. Journey 12: Create Task / Chore

- **Actor**: Home Owner, Home Admin, or Adult Member
- **Preconditions**: User has `tasks:create` permission.
- **Steps**:
  1. User navigates to Tasks & Chores and clicks "+ New Chore".
  2. Enters Title ("Vacuum Living Room"), Priority ("Medium"), Due Date ("Today, 6:00 PM").
  3. Leaves assignee unassigned ("Up for Grabs") or selects a specific member.
  4. Clicks "Create Task".
- **System Behaviour**:
  1. Inserts row into `tasks` table with `home_id`, `status = 'TODO'`, `created_by = current_user.id`.
  2. Emits task creation event to Home Dashboard.
- **Success State**: Task appears on the household chore board under "To Do".
- **Failure State**: Validation error if title is empty or due date is invalid.
- **Notifications**: If assigned to a member, dispatches instant notification to assignee.
- **Edge Cases**:
  - Recurring chore selected (e.g. "Every Sunday"): Sets `recurrence_rule = 'FREQ=WEEKLY;BYDAY=SU'`.

---

## 13. Journey 13: Assign / Reassign Task

- **Actor**: Home Owner or Home Admin
- **Preconditions**: User has `tasks:assign` permission; task exists.
- **Steps**:
  1. User opens task details for "Clean the Kitchen".
  2. Taps Assignee dropdown and selects "Sam (Teen)".
  3. Clicks "Save".
- **System Behaviour**:
  1. Updates `tasks.assigned_to = sam_user_id`.
  2. Logs assignment activity record.
  3. Dispatches push and in-app notification to Sam.
- **Success State**: Sam's avatar appears on task card; task surfaces in Sam's personal "My Chores" view.
- **Failure State**: 403 Forbidden if attempted by `CHILD` or `GUEST`.
- **Notifications**: Push alert to Sam: *"[Admin Name] assigned you a chore: 'Clean the Kitchen' (Due Today)."*
- **Edge Cases**:
  - Assignee is suspended or leaves home before completion: Task reverts to unassigned ("Up for Grabs").

---

## 14. Journey 14: Complete Task

- **Actor**: Assigned Member, Child, or Any Adult Member
- **Preconditions**: Task exists in `TODO` or `IN_PROGRESS` status.
- **Steps**:
  1. Sam finishes cleaning the kitchen; opens app and taps the checkmark on "Clean the Kitchen".
- **System Behaviour**:
  1. Updates `tasks.status = 'DONE'`, `completed_at = NOW()`.
  2. If task has a `recurrence_rule`, calculates next due timestamp and spawns the next `TODO` task instance.
  3. Increments user and household chore streak counters.
  4. Records activity in `task_activity_log`.
- **Success State**: Task moves to Completed section with celebration micro-animation; streak count increments.
- **Failure State**: Network failure saves state locally and retries.
- **Notifications**: In-app feed update: *"Sam completed 'Clean the Kitchen' 🎉"*.
- **Edge Cases**:
  - Completing an already completed task (double tap): Idempotent handler ignores second request.

---

## 15. Journey 15: Create Household Bill & Record Variable Payment

- **Actor**: Home Owner, Admin, or Adult Member
- **Preconditions**: User has `bills:create` / `bills:pay` permission.
- **Steps**:
  1. User navigates to Bills & Expenses and clicks "+ Add Bill" or selects preset "+ Electricity".
  2. Enters Expected Amount (`₹2,000.00`), Due Date (`2026-08-20`), Recurrence (`MONTHLY`, `SCHEDULED_DATE`), and assigns Vivek as responsible member.
  3. Clicks "Save Bill".
  4. When the actual BESCOM utility invoice arrives for `₹2,137.00`, Vivek clicks "Record Payment", enters `₹2,137.00`, selects UPI, and saves.
- **System Behaviour**:
  1. Inserts record into `bills` table bound to `home_id`.
  2. Recording payment appends an immutable transaction row in `bill_payments`.
  3. Automatically marks the current bill `PAID`, preserves the expected ₹2,000 baseline, and spawns the next month's recurring bill in `UNPAID` state.
- **Success State**: Current bill moves to Paid History; next month's bill appears on upcoming schedule; financial KPIs update in real-time.
- **Failure State**: 403 Forbidden if attempted across homes or by unauthorized members.

---

## 16. Journey 16: Partial Payment of Household Obligation

- **Actor**: Home Member
- **Preconditions**: Bill exists with expected amount `₹10,000.00`.
- **Steps**:
  1. Member opens "School Tuition Fee" bill.
  2. Clicks "Record Payment", enters `₹6,000.00`, selects Bank Transfer, and saves.
- **System Behaviour**:
  1. Appends `₹6,000.00` payment row to `bill_payments`.
  2. Updates `bills.amount_paid = 6000.00` and transitions status to `PARTIALLY_PAID`.
  3. Calculates remaining balance: `₹4,000.00`.
- **Success State**: Bill displays `PARTIALLY_PAID` status chip with clear indicator: *"Paid ₹6,000 of ₹10,000 • ₹4,000 Remaining"*.

---

## 17. Journey 17: Create Shared Household Event

- **Actor**: Home Owner, Home Admin, or Adult Member
- **Preconditions**: User has `calendar:create` permission.
- **Steps**:
  1. User navigates to Calendar & Events and clicks "+ Schedule Event".
  2. Enters Title ("HVAC Maintenance Inspection"), Date/Time ("Saturday 10:00 AM - 12:00 PM"), Category ("Maintenance"), Notes ("Technician phone: 555-0199").
  3. Clicks "Create Event".
- **System Behaviour**:
  1. Inserts row into `calendar_events` table bound to `home_id`.
  2. Emits event to household calendar stream.
- **Success State**: Event appears on the shared monthly/weekly calendar and on Saturday's Home Dashboard schedule.
- **Failure State**: Validation error if end time precedes start time.
- **Notifications**: Optional calendar notification to all adult members.
- **Edge Cases**:
  - Multi-day events: `is_all_day = TRUE` spans across target dates correctly.

---

## 18. Journey 18: Household Event Attendance / RSVP

- **Actor**: Any Household Member
- **Preconditions**: Calendar event exists.
- **Steps**:
  1. Member opens "Family Dinner & Movie Night" event.
  2. Taps RSVP button: "Attending" (or "Cannot Attend").
- **System Behaviour**:
  1. Inserts or updates record in `event_attendees` with `user_id`, `event_id`, and `status = 'ATTENDING'`.
- **Success State**: Member avatar displays with green check under Event Attendees list.
- **Failure State**: None.
- **Notifications**: Event organizer sees updated attendance tally.
- **Edge Cases**:
  - Member changes RSVP at the last minute: Replaces existing attendee record cleanly.

---

## 19. Journey 19: Receive & Triage Notifications

- **Actor**: Any Authenticated User
- **Preconditions**: Notifications exist in user's inbox.
- **Steps**:
  1. User taps Bell icon in app header displaying unread badge count `(3)`.
  2. Reviews list of alerts (e.g. chore assigned, low milk alert, bill reminder).
  3. Taps a specific notification to deep-link directly to that item.
  4. Taps "Mark All as Read".
- **System Behaviour**:
  1. `PATCH /api/v1/notifications/{id}/read` marks notification `is_read = TRUE`.
  2. Decrements unread badge count in real time.
- **Success State**: Unread badge clears; user navigates directly to actionable item.
- **Failure State**: Network retry.
- **Notifications**: None.
- **Edge Cases**:
  - Notification links to an entity that was deleted (e.g. chore deleted by admin): App shows graceful toast: *"This chore has been removed by an admin."*

---

## 20. Journey 20: Manage Subscription & Tier Upgrade

- **Actor**: Home Owner
- **Preconditions**: User is the verified `OWNER` of the Home workspace.
- **Steps**:
  1. Owner navigates to Home Settings $\rightarrow$ Subscription (`/settings/billing`).
  2. Reviews current plan (`FREE` tier: 1 Home, 5 members).
  3. Clicks "Upgrade to Premium".
  4. Selects Monthly or Annual billing, enters payment details via secure Stripe Elements checkout.
  5. Clicks "Confirm Subscription".
- **System Behaviour**:
  1. Backend creates Stripe Customer and initiates checkout session.
  2. Upon webhook confirmation `invoice.payment_succeeded`, updates `home_subscriptions.tier = 'PREMIUM'` and `status = 'ACTIVE'`.
  3. Lifts member caps and enables multi-home creation for the Owner.
- **Success State**: Premium badge unlocks; member limits removed immediately.
- **Failure State**: Card declined: Displays Stripe error message; tier remains `FREE`.
- **Notifications**: Transactional receipt email sent to Home Owner.
- **Edge Cases**:
  - Subscription cancellation: Retains Premium features until `current_period_end`, then gracefully downgrades without deleting existing data.

---

## 21. Journey 21: Quick Household Task Creation & Delegation

- **Actor**: Home Member
- **Preconditions**: User belongs to an active Home with `tasks:create` permission.
- **Steps**:
  1. Member opens Tasks tab on Web or Mobile.
  2. Types "Clean water filter" in the Quick Add bar and selects Priority: Normal.
  3. Optionally assigns the task to Karthika and sets Due Date: 20 Aug 2026.
  4. Taps "Add Task".
- **System Behaviour**:
  1. Validates title (min 2 chars) and asserts `home_id` tenant scoping.
  2. Inserts record into `tasks` table with `status = 'TODO'`.
  3. Dispatches real-time WebSocket / SSE update to family devices.
- **Success State**: Task appears on the shared Home Board and under Karthika's "My Tasks" view.
- **Failure State**: Returns 403 if user lacks permission.

---

## 22. Journey 22: Recurring Chore Execution & Next Occurrence Generation

- **Actor**: Assigned Home Member
- **Preconditions**: A recurring task exists on the Home board (e.g. *Service AC — Every 6 Months*).
- **Steps**:
  1. Member completes the service and opens Ozhzo Tasks.
  2. Taps checkbox on "Service AC".
- **System Behaviour**:
  1. Updates current task instance: `status = 'COMPLETED'`, `completed_by = current_user.id`, `completed_at = NOW()`.
  2. Evaluates recurrence definition (`recurrence_interval_days = 180`).
  3. Computes next due date based on completion date ($+180\text{ days}$).
  4. Spawns next recurring occurrence in `TODO` state linking `parent_recurring_task_id`.
- **Success State**: Current task moves to permanent completion history; next occurrence scheduled automatically.

---

## 23. Journey 23: Reviewing Maintenance History for Appliances

- **Actor**: Home Owner or Admin
- **Preconditions**: Household tasks have been completed over time.
- **Steps**:
  1. User opens Tasks and switches to the "Completed History" tab.
  2. Enters "filter" in the search box.
  3. Reviews chronological history of all filter cleanings, completion dates, and which family member performed them.
- **System Behaviour**:
  1. Queries `tasks` where `home_id = current_home.id` and `status = 'COMPLETED'`.
  2. Returns ordered results with member display names.
- **Success State**: Complete audit log displayed for appliance maintenance verification.

---

## 24. Journey 24: Scheduling a Shared Household Event
- **Actor**: Home Member
- **Preconditions**: User belongs to an active Home with `calendar:create` permission.
- **Steps**:
  1. Member opens Calendar tab on Web or Mobile.
  2. Uses Quick Add: "Grandmother's 80th Birthday", Date: 15 August 2026, toggles "All Day", selects Category: Birthday.
  3. Optionally selects family participants (Vivek, Karthika).
  4. Clicks "Save Event".
- **System Behaviour**:
  1. Validates `start_time` and `end_time` (expanding all-day boundaries according to `homes.timezone`).
  2. Validates that selected participants are active members of the same Home.
  3. Inserts record into `events` table and creates `event_participants` associations in `INVITED` status.
- **Success State**: Event appears instantly on the shared Home calendar for all members.

---

## 25. Journey 25: Viewing the Unified Home Calendar Projection
- **Actor**: Any Home Member
- **Preconditions**: User is logged in to their Home workspace.
- **Steps**:
  1. Member opens the Home Calendar view.
  2. Switches to "This Week" or "Agenda" view.
- **System Behaviour**:
  1. Frontend calls `GET /api/v1/homes/{home_id}/calendar/projection?start_date=...&end_date=...`.
  2. Backend performs parallel queries against `events`, `tasks`, and `bills` for the selected date window.
  3. Merges results in chronological order without duplicating records.
- **Success State**: Member sees a unified timeline of events (e.g. Doctor Visit at 10 AM), due bills (e.g. Electricity Bill due at 5 PM), and chores (e.g. Clean Filter due today) with distinct color badges.
