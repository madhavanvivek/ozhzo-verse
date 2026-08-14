# Ozhzo Verse — Production Operations & Maintenance Runbook (OPERATIONS.md)

**Operating Target**: 99.9% Uptime, Zero Data Loss, Sub-50ms API Latency  
**Target Audience**: DevOps Engineers, Site Reliability Engineers (SRE), On-Call Staff  

---

## 1. Health Checks & Probes

The core backend provides dedicated health and readiness endpoints mounted at `/api/v1/health`:

- **Liveness Probe**: `GET /api/v1/health`
  - Returns: `{"status": "healthy", "service": "ozhzo-verse-api", "version": "0.1.0"}`
  - Check interval: 10 seconds.
- **Readiness Probe**:
  - Checks live database connection pool (`SELECT 1`) and Redis socket ping (`PING`).
  - If either database or Redis fails, returns HTTP 503 Service Unavailable.

---

## 2. Logging & Distributed Tracing

### 2.1 Correlation IDs (`X-Request-ID`)
Every incoming HTTP request is assigned a unique UUID `X-Request-ID`. All log records written during that request cycle include the `correlation_id` in their metadata context.

### 2.2 Log Levels
- **INFO**: Request routing, authenticated user actions, status changes.
- **WARNING**: Rate-limit triggers, degraded Redis connections, token refresh conflicts.
- **ERROR**: Handled domain exceptions, failed third-party dispatches.
- **CRITICAL**: Database connection pool exhaustion, invalid production secrets, data corruption alerts.

---

## 3. Monitoring & Alert Thresholds

| Metric | Warning Threshold | Critical Threshold | Alert Action |
|---|---|---|---|
| **API Error Rate (5xx)** | $> 1\%$ for 5 min | $> 5\%$ for 2 min | SRE PagerDuty Alert |
| **API Latency (p95)** | $> 100$ms for 5 min | $> 300$ms for 2 min | Auto-scale API containers |
| **PostgreSQL Connection Pool** | $> 75\%$ capacity | $> 90\%$ capacity | Increase pool max size |
| **PostgreSQL Disk Usage** | $> 75\%$ storage | $> 85\%$ storage | Auto-expand EBS storage |
| **Redis Memory Utilization** | $> 70\%$ maxmemory | $> 85\%$ maxmemory | Evict volatile keys / Scale |
| **CPU / Memory (API pods)** | $> 70\%$ for 10 min | $> 85\%$ for 5 min | Kubernetes HPA trigger |

---

## 4. Backup & Disaster Recovery (DR)

### 4.1 Automated Database Backups
1. **Daily Full Logical Snapshot**:
   - `pg_dump -Fc -Z 9 ozhzo_verse_prod > /backups/daily_$(date +%Y%m%d).dump`
   - Encrypted and replicated to AWS S3 (Glacier storage class).
   - Retained for 30 days.
2. **Continuous WAL Archiving (Point-in-Time Recovery)**:
   - PostgreSQL Write-Ahead Logs (WAL) archived every 5 minutes.
   - Enables restoring database state to any specific second within the last 7 days.

### 4.2 Recovery Targets
- **Recovery Time Objective (RTO)**: $< 1$ hour.
- **Recovery Point Objective (RPO)**: $< 15$ minutes.

### 4.3 Database Restore Runbook
```bash
# 1. Stop API instances to prevent writes
docker stop ozhzo_api

# 2. Restore PostgreSQL snapshot
pg_restore --clean --if-exists -d ozhzo_verse_prod /backups/target_snapshot.dump

# 3. Start API instances and verify health
docker start ozhzo_api
curl -f http://localhost:8000/api/v1/health
```

---

## 5. Routine Maintenance Tasks

### Weekly Tasks
- **PostgreSQL VACUUM & ANALYZE**:
  ```sql
  VACUUM ANALYZE;
  ```
- **Inspect Slow Query Logs**: Analyze queries taking $>50$ms and verify compound index utilization.

### Monthly Tasks
- **Audit Token Blacklist TTLs**: Verify Redis memory consumption and eviction policies (`allkeys-lru`).
- **Test Database Restore in Staging**: Execute full dry-run backup restoration to confirm snapshot integrity.
