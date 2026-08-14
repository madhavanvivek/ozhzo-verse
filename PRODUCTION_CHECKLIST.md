# Ozhzo Verse — Production Go-Live Checklist (PRODUCTION_CHECKLIST.md)

**Target Release**: Ozhzo Verse MVP (v1.0.0)  
**Verification Target**: Zero critical/high vulnerabilities, clean builds, 100% test pass rate.

---

## 1. Pre-Flight Production Checklist

### 1.1 Security & Secrets
- [ ] `JWT_SECRET_KEY` generated with high-entropy 64-character secret (`openssl rand -base64 64`). Default development secret strictly removed.
- [ ] `DEBUG=false` confirmed in production environment.
- [ ] Interactive Swagger (`/docs`) and Redoc (`/redoc`) disabled in production.
- [ ] Database credentials isolated; PostgreSQL SSL (`sslmode=require`) enforced.
- [ ] Redis protected with strong auth password (`REDIS_PASSWORD`) and TLS (`rediss://`).
- [ ] CORS `ALLOWED_ORIGINS` restricted to verified production domains (`https://app.ozhzo.com`).
- [ ] HTTP Security Headers verified (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`).

### 1.2 Database & Data Integrity
- [ ] Database migrations executed (`alembic upgrade head`).
- [ ] Multi-tenant compound search indexes verified in PostgreSQL:
  - `idx_inv_items_home_search` on `(home_id, name)`
  - `idx_shopping_items_search` on `(home_id, name)`
  - `idx_tasks_home_search` on `(home_id, title)`
  - `idx_bills_home_search` on `(home_id, title)`
  - `idx_events_home_search` on `(home_id, title)`
  - `idx_home_members_lookup` on `(home_id, user_id, status)`
- [ ] Automated daily logical backups and continuous WAL archiving active on AWS S3.
- [ ] Connection pool sizing configured (`pool_size=20`, `max_overflow=10`).

### 1.3 Quality & Builds
- [ ] Full automated test suite passes: `bash scripts/test.sh` (100% pass rate).
- [ ] Linter & formatting checks pass: `bash scripts/lint.sh` (0 errors).
- [ ] Production monorepo build compiles cleanly: `bash scripts/build.sh`.
- [ ] Next.js production bundle size verified with optimization.

### 1.4 Monitoring & Observability
- [ ] Centralized structured logging configured with `correlation_id` (`X-Request-ID`).
- [ ] Health check endpoint (`/api/v1/health`) verified with readiness probes.
- [ ] Error tracking service (e.g. Sentry / Datadog) connected.
- [ ] SRE alert thresholds configured for 5xx error spikes and p95 latency $>100$ms.

---

## 2. Go-Live Execution Runbook

| Step | Action | Command / Procedure | Verification |
|---|---|---|---|
| **1** | Provision DB & Redis | Run AWS RDS PostgreSQL & ElastiCache Redis | `pg_isready` & `redis-cli ping` |
| **2** | Run DB Migrations | Execute schema migration | `alembic upgrade head` |
| **3** | Deploy Backend Pods | Roll out container images | `curl -f https://api.ozhzo.com/api/v1/health` returns `200 OK` |
| **4** | Deploy Web Frontend | Roll out Next.js production build | Visit `https://app.ozhzo.com` in browser |
| **5** | Enable Nginx / Edge Proxy | Configure DNS & TLS 1.3 certs | Verify A+ score on SSL Labs |
| **6** | Execute Smoke Tests | Run automated Post-Launch Smoke Suite | 100% smoke test pass |

---

## 3. Post-Launch Smoke Test Plan

1. **Authentication**: Register test user, log in, refresh token, log out.
2. **Home Setup**: Create new home workspace; verify creator assigned `OWNER`.
3. **Invitations**: Send member invitation, accept with second user account.
4. **Inventory**: Add item with minimum threshold; test low stock notification dispatch.
5. **Shopping**: Convert low-stock item to shopping list item; check item off.
6. **Tasks & Chores**: Create recurring chore; complete chore; verify next iteration spawns.
7. **Bills & Reminders**: Schedule recurring utility bill; record payment; verify payment history.
8. **Calendar**: Schedule family gathering; test RSVP response.
9. **Unified Search**: Execute keyword search across all 5 domains; verify Child role bill redaction.
10. **Subscription**: Check 1-year free admin trial banner and additional member seat stepper.

---

## 4. Rollback Sign-Off

If severe unrecoverable errors occur during the go-live window:
1. Roll back API container tags to previous stable version.
2. Revert database schema if needed: `alembic downgrade -1`.
3. Post incident status update on status page.
