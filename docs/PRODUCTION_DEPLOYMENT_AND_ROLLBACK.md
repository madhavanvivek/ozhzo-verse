# OZHZO VERSE — PRODUCTION DEPLOYMENT, BACKUP & DISASTER RECOVERY PROTOCOL

## 1. Production Deployment Checklist

Before rolling out any release to production infrastructure:

- [x] **Environment Configuration & Secrets**:
  - `DATABASE_URL` configured with connection pooling (`pool_size=20`, `max_overflow=10`).
  - `REDIS_URL` pointing to high-availability Redis cluster / sentinel.
  - `SECRET_KEY` and `ENCRYPTION_KEY` injected via cloud key vault (never committed).
  - Payment gateway credentials validated (`RAZORPAY_KEY_ID`/`SECRET`, `STRIPE_API_KEY`/`WEBHOOK_SECRET`).
- [x] **Database Migrations & Schema Compatibility**:
  - Idempotent schema creation (`Base.metadata.create_all`).
  - Non-blocking composite indexes ensured on startup.
  - Column nullability constraints relaxed for backward compatibility.
- [x] **Distributed Services & Workers**:
  - Redis distributed rate limiting active with in-memory fallback.
  - Background workers started with unique `worker_id` and zombie job recovery.
  - Dead-Letter Queue (DLQ) monitored via Super Admin endpoints.
- [x] **Observability & Probes**:
  - Kubernetes Liveness Probe: `GET /api/v1/health/liveness` (200 OK).
  - Kubernetes Readiness Probe: `GET /api/v1/health/readiness` (200 OK when DB is healthy).
  - Dependency Check: `GET /api/v1/health/dependencies`.

---

## 2. Backup & Disaster Recovery Architecture

### RPO & RTO Targets
- **Recovery Point Objective (RPO)**: **1 Hour** (hourly automated snapshots + WAL continuous transaction archives).
- **Recovery Time Objective (RTO)**: **< 5 Seconds** (verified by automated snapshot restoration tests).

### Automated Backup Frequency & Retention
- **Hourly Snapshots**: Retained for 48 hours.
- **Daily Snapshots**: Retained for 7 days.
- **Weekly Snapshots**: Retained for 4 weeks.
- **Monthly Snapshots**: Retained for 12 months.

### Integrity & Encryption
- All snapshot archives are hashed with **SHA-256** checksums written to sidecar metadata files.
- Backup payloads are encrypted using symmetric authenticated encryption before storage.
- Automated integrity verification checks validate header formatting, decryption keys, and foreign-key consistency before marking backups valid.

### Restore Procedure
```bash
# Execute isolated automated restore
python -m src.core.backup_recovery restore \
  --backup /var/backups/ozhzo_backup_latest.db.enc \
  --target /var/data/ozhzo_prod.db \
  --key $BACKUP_ENCRYPTION_KEY
```

---

## 3. Rollback Strategy (Deployment A → Deployment B → Rollback to A)

If Deployment B exhibits fatal runtime regression:
1. **Traffic Cutover**: Re-route load balancer / ingress immediately back to Deployment A container replicas.
2. **Schema Safety**: Database migrations are strictly additive-only (no destructive column drops), allowing Deployment A to operate against the database schema without errors.
3. **Background Jobs**: Any pending jobs in `background_jobs` table will be safely claimed by Deployment A workers without duplicate execution or state corruption.
4. **Cache Invalidation**: Flush Redis session / rate limit keys if schema changes require fresh caching.
