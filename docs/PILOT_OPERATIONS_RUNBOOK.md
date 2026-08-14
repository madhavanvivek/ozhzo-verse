# Ozhzo Verse — MVP Pilot Operations Runbook

**Document**: Pilot Operations Runbook  
**Classification**: Operations & Deployment Standard Operating Procedure (SOP)  
**Target**: Pilot Operations Team, System Administrators  
**Version**: 0.1.0-pilot.1  

---

## Section A: Pre-Deployment Checklist
- [ ] Production host provisioned with Ubuntu 22.04 LTS+ / macOS / container runtime.
- [ ] PostgreSQL 16+ instance running with `uuid-ossp` and `pgcrypto` extensions enabled.
- [ ] Redis 7+ instance running for transient cache and rate limiting.
- [ ] TLS certificate configured (Let's Encrypt / Cloudflare SSL) for HTTPS.
- [ ] Domain names mapped (`api.ozhzoverse.com`, `app.ozhzoverse.com`).
- [ ] Quality gates verified (`contracts`, `tests`, `lint`, `build` 100% passing).

---

## Section B: Environment Configuration
Create a secure production `.env` file based on `.env.example`:

```bash
# Production .env Checklist
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

API_PORT=8000
API_HOST=0.0.0.0
ALLOWED_ORIGINS=https://app.ozhzoverse.com

NEXT_PUBLIC_API_BASE_URL=https://api.ozhzoverse.com/api/v1
NEXT_PUBLIC_APP_NAME="Ozhzo Verse"

# Generate with: openssl rand -hex 32
JWT_SECRET_KEY=<SECURE_PRODUCTION_32_CHAR_SECRET>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

DATABASE_URL=postgresql+asyncpg://<db_user>:<db_pass>@<db_host>:5432/<db_name>
DATABASE_URL_SYNC=postgresql://<db_user>:<db_pass>@<db_host>:5432/<db_name>

REDIS_URL=redis://:<redis_pass>@<redis_host>:6379/0
```

---

## Section C: Database Initialization & Schema Verification
Execute the canonical DDL against the clean production PostgreSQL database:

```bash
# 1. Initialize PostgreSQL Extensions & DDL Schema
psql -h <db_host> -U <db_user> -d <db_name> -f database/schema.sql

# 2. Verify Core Tables
psql -h <db_host> -U <db_user> -d <db_name> -c "\dt"
# Must list: users, user_profiles, homes, home_members, locations, inventory_items, stock_movements, tasks, bills, events, audit_logs
```

---

## Section D: Automated Backup Verification
Set up a daily automated pg_dump cron job:

```bash
# Daily backup cron script
#!/bin/bash
BACKUP_DIR="/var/backups/ozhzo"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p $BACKUP_DIR
pg_dump -h <db_host> -U <db_user> -F c -b -v -f "$BACKUP_DIR/ozhzo_prod_$TIMESTAMP.dump" <db_name>

# Retain 14 days of backups
find $BACKUP_DIR -name "*.dump" -mtime +14 -exec rm {} \;
```

---

## Section E: OTP & SMS Provider Configuration
In production, OTP delivery requires an SMS Gateway (e.g. AWS SNS, Twilio, MSG91):
1. Configure SMS provider credentials in backend environment variables.
2. In production, mock OTPs (e.g. `123456`) are **disabled**.
3. OTP attempts are rate-limited to 5 per 10-minute window per phone number.

---

## Section F: Super Admin Initial Setup
Bootstrap the initial Super Admin account using the secure CLI script or direct SQL registration:

```bash
# Promote verified initial admin account
psql -h <db_host> -U <db_user> -d <db_name> -c "UPDATE users SET is_super_admin = TRUE, system_role = 'SUPER_ADMIN' WHERE email = 'admin@ozhzoverse.com';"
```

---

## Section G: Pilot Household Onboarding Procedure
For each of the 5–10 pilot households:
1. **Primary Homeowner Registration**:
   - Navigate to `https://app.ozhzoverse.com/register`.
   - Complete mobile registration & profile creation.
2. **Home Workspace Creation**:
   - Name home (e.g. *"Madhavan Family Home"*), confirm currency and timezone.
3. **Family Member Invitations**:
   - In Settings ➔ Members, invite spouse/family members via email or SMS link.
4. **Starter Pack Seeding**:
   - Select common starter items (Rice, Milk, Electricity Bill, Water Filter chore).
5. **Initial Value Verification**:
   - Verify Home Memory search returns first stored tool in $< 60$ seconds.

---

## Section H: Real-Time Monitoring & Diagnostic Logging
- **Health Checks**:
  - Liveness: `GET https://api.ozhzoverse.com/api/v1/health/live`
  - Readiness: `GET https://api.ozhzoverse.com/api/v1/health/ready`
- **Application Logs**:
  - Tail structured JSON logs filtering by `X-Request-ID` or `correlation_id`.
  - Errors automatically capture stack traces with domain error codes.

---

## Section I: Bug Severity Classification & Escalation
- **P0 (Critical Blocker)**: Data loss, security breach, financial discrepancy, cross-home data leakage $\rightarrow$ **Immediate hotfix within 2 hours**.
- **P1 (High Severity)**: Broken core loop (cannot complete task, cannot add inventory, search failure) $\rightarrow$ **Fix within 24 hours**.
- **P2 (Medium)**: UX friction, minor layout distortion, slow response $\rightarrow$ **Schedule in weekly pilot patch**.
- **P3 (Low)**: Cosmetic, typo, non-essential alignment $\rightarrow$ **Log for post-pilot Phase 9**.

---

## Section J: Rollback Procedure
If a critical defect is identified during pilot deployment:
1. Revert web and API containers to previous release tag (e.g. `git checkout v0.1.0-pilot.0`).
2. Restart backend service.
3. If database schema was affected, restore from latest clean snapshot (Section K).

---

## Section K: Backup Restore Procedure

```bash
# Emergency Database Restore
# 1. Terminate active backend connections
psql -h <db_host> -U <db_user> -d <db_name> -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '<db_name>' AND pid <> pg_backend_pid();"

# 2. Restore from pg_dump snapshot
pg_restore -h <db_host> -U <db_user> -d <db_name> -v -c "$BACKUP_DIR/ozhzo_prod_<TIMESTAMP>.dump"

# 3. Verify health
curl -f https://api.ozhzoverse.com/api/v1/health/ready
```

---

## Section L: Pilot Completion & Review Procedure
At the end of the 2–4 week pilot window:
1. Export anonymized telemetry and feedback submissions via `GET /api/v1/admin/feedback`.
2. Conduct the 10 structured interviews using [`PILOT_FEEDBACK_GUIDE.md`](file:///Users/vivek/ozHzo/ozhzo_verse/docs/PILOT_FEEDBACK_GUIDE.md).
3. Synthesize findings into the **MVP Pilot Post-Mortem Report**.
