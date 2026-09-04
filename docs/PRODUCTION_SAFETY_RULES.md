# OZHZO VERSE — PRODUCTION SAFETY RULES

---

## 1. Principles of Real-World Household Data Protection

During the Private Pilot, all data belongs to actual households. Data corruption, leakage, or accidental deletion violates trust and privacy guarantees. The following rules are mandatory and non-negotiable.

---

## 2. Core Safety Mandates

### Rule 1: No Destructive Test Scripts Against Production
- Automated integration test suites that create and drop tables or wipe entities must NEVER be executed against production databases.
- Test suites must use designated staging databases or ephemeral test fixtures.

### Rule 2: No Direct Unaudited SQL In Production
- No manual `UPDATE` or `DELETE` SQL queries may be run directly against the production database without a signed change request and automated snapshot backup immediately preceding execution.
- All administrative actions must be performed through audited Super Admin API endpoints (`audit_logs` table).

### Rule 3: Zero Exposure of Household Data
- Super Admin inspection consoles must never display un-hashed passwords, session secrets, or full payment credentials.
- Multi-tenant boundary rules must be strictly enforced: a user from Home A cannot access Home B under any circumstances.

### Rule 4: Sanitization & Safe Demarcation of AI Inputs
- All user-generated text (task titles, notes, memory entries) passed to language models must be demarcated within `<untrusted_household_content>` tags and sanitized against prompt injection.

### Rule 5: Non-Destructive Additive Schema Migrations
- Schema migrations must only be additive (e.g. adding nullable columns, new tables, or composite indexes).
- Columns and tables must never be dropped in a production rollout without a multi-release deprecation cycle.

### Rule 6: Pre-Deployment Backup Mandate
- Before any application release or schema migration is applied to production, an online encrypted backup snapshot must be verified.

### Rule 7: Controlled Pilot Deletion Protocol
- If a pilot user requests account deletion under GDPR/CCPA, deletion must be executed through the verified privacy engine ([`DataGovernanceManager`](file:///Users/vivek/ozHzo/ozhzo_verse/services/api/src/core/data_governance.py)), which records an immutable cryptographic audit receipt while purging PII.
