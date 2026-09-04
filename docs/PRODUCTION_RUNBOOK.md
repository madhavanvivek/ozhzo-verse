# OZHZO VERSE — PRODUCTION RUNBOOK

---

## 1. System Overview & Architecture Topology

Ozhzo Verse is a modern multi-tenant household management and intelligence platform built with a high-performance Python FastAPI backend and a Next.js 14 App Router frontend.

```
Internet (Users / Admin / Webhooks)
         │ HTTPS (TLS 1.3)
         ▼
[ Cloudflare / Reverse Proxy Edge ]
         │ (WAF, SSL Termination, DDoS Protection)
         ▼
[ Next.js 14 Web Frontend ] ─────────► [ FastAPI Application API ]
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   ▼                             ▼                             ▼
         [ SQLite WAL / PostgreSQL ]    [ Redis Cluster (Valkey) ]     [ AI & Payment Gateways ]
         (Authoritative Storage)        (Distributed Rate Limits,     (Gemini / OpenAI / Anthropic,
                                         Session & Caching)            Stripe / Razorpay)
```

---

## 2. Infrastructure & Environment Configuration Audit

| Configuration Variable | Classification | Development Default | Staging Value | Production Requirement | Validation Status |
|---|---|---|---|---|---|
| `ENVIRONMENT` | Non-Secret | `development` | `staging` | `production` | ✅ Verified |
| `API_BASE_URL` | Non-Secret | `http://localhost:8000` | `https://staging-api.ozhzo.com` | `https://api.ozhzo.com` | ✅ Verified |
| `FRONTEND_BASE_URL` | Non-Secret | `http://localhost:3000` | `https://staging.ozhzo.com` | `https://app.ozhzo.com` | ✅ Verified |
| `DATABASE_URL` | **SECRET** | `sqlite:///ozhzo.db` | `sqlite:///staging.db` | Managed PostgreSQL / Encrypted Volume | ✅ Verified |
| `REDIS_URL` | **SECRET** | `redis://localhost:6379/0` | `redis://staging-redis:6379/0` | `rediss://prod-cluster:6379` (TLS) | ✅ Verified |
| `JWT_SECRET_KEY` | **SECRET** | Local dev key | Staging key | 256-bit cryptographically secure secret | ✅ Verified |
| `COOKIE_SECURE` | Non-Secret | `False` | `True` | `True` (Strict HTTPS) | ✅ Verified |
| `CORS_ORIGINS` | Non-Secret | `["http://localhost:3000"]` | `["https://staging.ozhzo.com"]` | `["https://app.ozhzo.com"]` | ✅ Verified |
| `BACKUP_ENCRYPTION_KEY`| **SECRET** | Dev key | Staging key | KMS-managed AES-GCM Key | ✅ Verified |
| `RAZORPAY_KEY_SECRET` | **SECRET** | Sandbox test key | Sandbox test key | Provider Sandbox $\to$ Live Production Key | ✅ Verified |
| `GEMINI_API_KEY` | **SECRET** | Test key | Staging key | Quota-controlled Enterprise Key | ✅ Verified |

---

## 3. Routine Operations & Runbook Procedures

### A. Health & Readiness Verification
- **Liveness Probe**: `GET /health` $\to$ Returns HTTP 200 `{"status": "healthy"}`.
- **Readiness Probe**: `GET /health/readiness` $\to$ Inspects database connectivity, Redis connection, and background job queue depth. Returns HTTP 200 when ready, HTTP 503 if degraded.

### B. Automated Backup Execution & Verification
- Backups execute hourly via [`BackupRecoveryManager.create_database_backup`](file:///Users/vivek/ozHzo/ozhzo_verse/services/api/src/core/backup_recovery.py).
- Integrity checksums (`SHA-256`) and encryption envelopes (`OZHZO_ENC_V1:`) are validated automatically upon snapshot generation.
- Pruning routine enforces tiered retention (48 hourly, 7 daily, 4 weekly, 12 monthly).

### C. Worker & Scheduler Operations
- Background workers consume from the durable job queue with distributed locking (`locked_by`, `locked_at`).
- Stale/zombie locks (>30s) are automatically reclaimed by healthy worker pods.
- Dead-letter queue (DLQ) jobs can be inspected and retried via `POST /admin/system/failed-jobs/{id}/retry`.

### D. AI Quota & Budget Management
- Daily and monthly household token quotas are tracked per home.
- If a home reaches its tiered AI quota, graceful fallback responses are rendered without breaking core household CRUD functions.

---

## 4. Disaster Recovery Procedure

1. **Detect Corruption / Outage**: Readiness probe emits 503 or database file is inaccessible.
2. **Isolate Traffic**: Place load balancer in maintenance mode.
3. **Select Latest Encrypted Snapshot**: Query external backup vault for latest verified `.enc` artifact.
4. **Execute Restoration**:
   ```bash
   python -m src.core.backup_recovery restore --backup-file /vault/backup_latest.enc --target-db /data/production.db --key $BACKUP_ENCRYPTION_KEY
   ```
5. **Run Schema & Consistency Check**: Validate `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
6. **Execute Smoke Tests**: Run `pytest tests/test_production_smoke.py`.
7. **Re-enable Traffic**: Open traffic on load balancer edge.
