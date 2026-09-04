# OZHZO VERSE — ANALYTICS & PRODUCT TELEMETRY SPECIFICATION

---

## 1. Privacy & Boundary Guarantees

- **Multi-Tenant Isolation**: All analytics events capture `home_id` and `user_id` as anonymized UUIDs.
- **Zero PII Exposure**: Telemetry never records raw passwords, payment card numbers, sensitive health/biometric details, or full personal chat text.
- **Aggregated Reporting**: Operational and product KPI metrics are computed at the household and tenant boundary.

---

## 2. Minimum Required Event Taxonomy

### A. Authentication & Onboarding
- `signup_started`: `{ "channel": "web_direct", "timestamp": ISO }`
- `signup_completed`: `{ "user_id": UUID, "auth_provider": "local" }`
- `verification_completed`: `{ "user_id": UUID, "method": "sms_otp" }`
- `login_completed`: `{ "user_id": UUID, "session_type": "standard" }`

### B. Home Identity & Membership
- `home_created`: `{ "home_id": UUID, "user_id": UUID, "plan": "FREE" }`
- `home_joined`: `{ "home_id": UUID, "user_id": UUID, "role": "MEMBER" }`
- `member_invited`: `{ "home_id": UUID, "role": "MEMBER", "channel": "link" }`
- `invitation_accepted`: `{ "home_id": UUID, "invite_token_id": UUID }`
- `home_switched`: `{ "from_home_id": UUID, "to_home_id": UUID }`

### C. Household Core Operations
- `task_created`: `{ "home_id": UUID, "priority": "MEDIUM", "has_due_date": true }`
- `task_completed`: `{ "home_id": UUID, "duration_to_complete_hours": 4.5 }`
- `bill_created`: `{ "home_id": UUID, "amount": 120.00, "currency": "USD" }`
- `bill_paid`: `{ "home_id": UUID, "payment_method": "CASH/BANK" }`
- `shopping_item_added`: `{ "home_id": UUID, "category": "GROCERIES" }`
- `shopping_item_completed`: `{ "home_id": UUID, "auto_restocked_to_inventory": true }`
- `inventory_item_added`: `{ "home_id": UUID, "tracking_type": "CONSUMABLE" }`
- `calendar_event_created`: `{ "home_id": UUID, "is_recurring": false }`

### D. AI Assistant & Planning Agent
- `ai_opened`: `{ "home_id": UUID, "surface": "HEADER_WIDGET" }`
- `ai_message_sent`: `{ "home_id": UUID, "has_context": true }`
- `ai_proposal_created`: `{ "home_id": UUID, "action_type": "ADD_SHOPPING_ITEM" }`
- `ai_action_confirmed`: `{ "home_id": UUID, "proposal_id": UUID }`
- `ai_action_rejected`: `{ "home_id": UUID, "proposal_id": UUID }`

### E. Automations & Memory Vault
- `automation_created`: `{ "home_id": UUID, "trigger_type": "SCHEDULED_TIME" }`
- `automation_executed`: `{ "home_id": UUID, "status": "SUCCESS" }`
- `memory_created`: `{ "home_id": UUID, "category": "PREFERENCE" }`

### F. Monetization & Subscriptions
- `pricing_viewed`: `{ "home_id": UUID, "current_plan": "FREE" }`
- `checkout_started`: `{ "home_id": UUID, "plan_code": "PRO_MONTHLY" }`
- `payment_success`: `{ "home_id": UUID, "amount": 9.99, "currency": "USD" }`
- `subscription_activated`: `{ "home_id": UUID, "plan_code": "PRO_MONTHLY" }`
