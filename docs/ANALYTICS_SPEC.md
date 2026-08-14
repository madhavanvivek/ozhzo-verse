# Ozhzo Verse — Analytics & Telemetry Event Specification (ANALYTICS_SPEC.md)

**Document Version**: 1.0.0 (MVP Baseline)  
**Standard**: Privacy-by-Design & Data Minimization (GDPR / CCPA Compliant)  
**Event Naming Convention**: `snake_case` (e.g. `account_created`, `task_completed`)  

---

## 1. Analytics Privacy & Data Governance Principles

1. **Strict Data Minimization**: Only operational telemetry necessary to evaluate user engagement, feature adoption, and retention funnels is captured.
2. **Zero PII in Event Payloads**:
   - Never track raw passwords, email addresses, phone numbers, or user full names in event properties.
   - User identity is tracked strictly via pseudonymized UUIDs (`user_id`).
3. **Financial & Note Privacy**:
   - Bill dollar amounts and personal task/inventory note text are **never** emitted in telemetry events. Only categories, recurrence frequencies, and completion timestamps are logged.
4. **Multi-Tenant Context**:
   - All household actions include `home_id` to measure multi-member collaboration dynamics per household without exposing inter-home relationships.

---

## 2. Global Event Context / Envelope

Every event dispatched to the analytics pipeline includes the following base context:

```json
{
  "event_id": "uuid4",
  "event_name": "string",
  "timestamp": "2026-08-13T14:30:00.000Z",
  "user_id": "uuid4",
  "home_id": "uuid4_or_null",
  "client": {
    "platform": "web | ios | android",
    "app_version": "1.0.0",
    "os": "macOS | iOS | Android | Windows | Linux",
    "locale": "en-US",
    "timezone": "America/New_York"
  },
  "properties": {}
}
```

---

## 3. Comprehensive Event Catalog

---

### 1. `account_created`
- **Trigger**: Fired immediately when a new user registers an account (`POST /api/v1/auth/register`).
- **User Identifier**: `user_id` (New User UUID)
- **Home Identifier**: `null` (Home not created yet)
- **Properties**:
  - `auth_method`: `string` (`"password"`, `"google"`, `"apple"`)
  - `has_invited_context`: `boolean` (True if registration originated from an invite link)
- **Privacy Considerations**: Email, name, and IP address are strictly excluded from event properties.

---

### 2. `home_created`
- **Trigger**: Fired when a user instantiates a new Home workspace (`POST /api/v1/homes`).
- **User Identifier**: `user_id` (Owner UUID)
- **Home Identifier**: `home_id` (New Home UUID)
- **Properties**:
  - `currency`: `string` (e.g. `"USD"`, `"EUR"`, `"GBP"`)
  - `timezone`: `string` (e.g. `"America/New_York"`)
  - `is_first_home`: `boolean`
- **Privacy Considerations**: Home street address and custom home title are excluded.

---

### 3. `member_invited`
- **Trigger**: Fired when a Home Admin or Owner creates an invitation link (`POST /api/v1/homes/{home_id}/invitations`).
- **User Identifier**: `user_id` (Inviter UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `role_assigned`: `string` (`"ADMIN"`, `"MEMBER"`, `"CHILD"`, `"GUEST"`)
  - `total_active_members_count`: `integer`
  - `delivery_channel`: `string` (`"copy_link"`, `"email"`, `"qr_code"`)
- **Privacy Considerations**: Invitee email address is masked or omitted.

---

### 4. `member_joined`
- **Trigger**: Fired when an invitee successfully accepts an invite token (`POST /api/v1/invitations/{token}/accept`).
- **User Identifier**: `user_id` (Joined User UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `role`: `string` (`"ADMIN"`, `"MEMBER"`, `"CHILD"`, `"GUEST"`)
  - `days_since_invite_created`: `integer`
  - `new_member_count`: `integer`
- **Privacy Considerations**: Only anonymous role and duration metrics are captured.

---

### 5. `inventory_item_added`
- **Trigger**: Fired when a household supply is created (`POST /api/v1/homes/{home_id}/inventory/items`).
- **User Identifier**: `user_id` (Creator UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `category_name`: `string` (e.g. `"Pantry"`, `"Fridge"`, `"Cleaning"`)
  - `has_min_threshold`: `boolean`
  - `has_expiry_date`: `boolean`
  - `has_location`: `boolean`
  - `measurement_unit`: `string` (`"pcs"`, `"kg"`, `"liters"`)
- **Privacy Considerations**: Item custom text and storage location strings are omitted; only boolean flags and category groupings are emitted.

---

### 6. `inventory_item_low_stock`
- **Trigger**: Fired when an inventory item stock calculation transitions to `LOW_STOCK` or `OUT_OF_STOCK`.
- **User Identifier**: `user_id` (User who triggered quantity decrement or system evaluator)
- **Home Identifier**: `home_id`
- **Properties**:
  - `category_name`: `string`
  - `status`: `string` (`"LOW_STOCK"`, `"OUT_OF_STOCK"`, `"EXPIRED"`)
  - `days_since_added`: `integer`
- **Privacy Considerations**: Zero note text or private identifiers captured.

---

### 7. `shopping_item_added`
- **Trigger**: Fired when an item is added to a shopping list (`POST /api/v1/homes/{home_id}/shopping/lists/{list_id}/items`).
- **User Identifier**: `user_id`
- **Home Identifier**: `home_id`
- **Properties**:
  - `priority`: `string` (`"LOW"`, `"MEDIUM"`, `"HIGH"`, `"URGENT"`)
  - `source`: `string` (`"manual_entry"`, `"converted_from_inventory"`)
  - `is_assigned`: `boolean`
- **Privacy Considerations**: Custom brand names and item descriptions are excluded.

---

### 8. `shopping_item_purchased`
- **Trigger**: Fired when a shopping list item is checked off as purchased (`PATCH /api/v1/homes/{home_id}/shopping/items/{item_id}/check`).
- **User Identifier**: `user_id`
- **Home Identifier**: `home_id`
- **Properties**:
  - `priority`: `string`
  - `is_concurrent_session`: `boolean` (True if $\ge 2$ members active in home within last 5 minutes)
  - `hours_since_added`: `number`
  - `list_completion_percentage`: `integer`
- **Privacy Considerations**: Item text excluded; only list progress metrics emitted.

---

### 9. `task_created`
- **Trigger**: Fired when a chore or household routine is created (`POST /api/v1/homes/{home_id}/tasks`).
- **User Identifier**: `user_id` (Creator UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `priority`: `string` (`"LOW"`, `"MEDIUM"`, `"HIGH"`, `"URGENT"`)
  - `has_due_date`: `boolean`
  - `recurrence_rule`: `string` (`"ONE_TIME"`, `"DAILY"`, `"WEEKLY"`, `"MONTHLY"`)
  - `is_assigned_to_other`: `boolean`
- **Privacy Considerations**: Task title and checklist details are excluded.

---

### 10. `task_completed`
- **Trigger**: Fired when a task is marked completed (`PATCH /api/v1/homes/{home_id}/tasks/{task_id}/complete`).
- **User Identifier**: `user_id` (Completing User UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `priority`: `string`
  - `recurrence_rule`: `string`
  - `is_completed_on_time`: `boolean`
  - `is_completed_by_assignee`: `boolean`
- **Privacy Considerations**: Only timeliness and assignment metadata logged.

---

### 11. `bill_created`
- **Trigger**: Fired when a recurring utility or household bill is added (`POST /api/v1/homes/{home_id}/bills`).
- **User Identifier**: `user_id`
- **Home Identifier**: `home_id`
- **Properties**:
  - `category`: `string` (`"Utilities"`, `"Rent"`, `"Insurance"`, `"Internet"`, `"Subscription"`, `"Other"`)
  - `recurrence_interval`: `string` (`"MONTHLY"`, `"QUARTERLY"`, `"ANNUAL"`, `"ONE_TIME"`)
  - `reminder_lead_days`: `integer[]` (e.g. `[7, 3, 1]`)
  - `has_default_payer`: `boolean`
- **Privacy Considerations**: **CRITICAL PRIVACY RULE** — Exact bill dollar amounts, account numbers, and payee names are **strictly forbidden** from telemetry.

---

### 12. `bill_paid`
- **Trigger**: Fired when a bill payment is recorded (`POST /api/v1/homes/{home_id}/bills/{bill_id}/payments`).
- **User Identifier**: `user_id` (Payer UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `category`: `string`
  - `recurrence_interval`: `string`
  - `days_before_or_after_due`: `integer` (Negative = paid early; Positive = paid overdue)
- **Privacy Considerations**: Dollar payment amounts and receipt notes are never emitted.

---

### 13. `event_created`
- **Trigger**: Fired when a family event is scheduled (`POST /api/v1/homes/{home_id}/events`).
- **User Identifier**: `user_id`
- **Home Identifier**: `home_id`
- **Properties**:
  - `is_all_day`: `boolean`
  - `has_location`: `boolean`
  - `participants_count`: `integer`
  - `lead_time_days`: `integer` (Days between creation and event start)
- **Privacy Considerations**: Event title, description, and location text are omitted.

---

### 14. `notification_opened`
- **Trigger**: Fired when a user clicks/opens an in-app or system notification (`PATCH /api/v1/notifications/{id}/read`).
- **User Identifier**: `user_id`
- **Home Identifier**: `home_id`
- **Properties**:
  - `notification_type`: `string` (`"TASK_ASSIGNED"`, `"BILL_REMINDER"`, `"LOW_STOCK"`, `"EVENT_REMINDER"`, `"HOME_INVITATION"`, `"SYSTEM"`)
  - `minutes_since_dispatched`: `integer`
- **Privacy Considerations**: Body copy excluded; only type category tracked.

---

### 15. `subscription_viewed`
- **Trigger**: Fired when a Home Admin views the subscription & entitlements page (`GET /api/v1/subscriptions/homes/{home_id}`).
- **User Identifier**: `user_id`
- **Home Identifier**: `home_id`
- **Properties**:
  - `is_in_introductory_trial`: `boolean`
  - `days_remaining_in_trial`: `integer`
  - `total_active_members`: `integer`
  - `active_paid_seats`: `integer`
- **Privacy Considerations**: Only seat count and trial status captured.

---

### 16. `subscription_started`
- **Trigger**: Fired when paid member seats are configured or upgraded (`POST /api/v1/subscriptions/homes/{home_id}/seats`).
- **User Identifier**: `user_id` (Admin/Owner UUID)
- **Home Identifier**: `home_id`
- **Properties**:
  - `plan_code`: `string` (`"HOME_STANDARD_ANNUAL"`)
  - `paid_member_seats_count`: `integer`
  - `is_during_intro_trial`: `boolean`
- **Privacy Considerations**: No credit card or billing address data is ever captured in product analytics.
