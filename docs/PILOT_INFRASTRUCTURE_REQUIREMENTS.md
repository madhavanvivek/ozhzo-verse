# Ozhzo Verse — Pilot Infrastructure Requirements Analysis

**Document**: Actual Infrastructure Requirements Analysis  
**Application Version**: `0.1.0-pilot.1`  
**Purpose**: Codebase-grounded infrastructure audit (Zero phantom infrastructure)  

---

## 1. Actual Codebase Dependency Audit

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ACTUAL ARCHITECTURE & RUNTIME SERVICES                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  [CORE] FastAPI API Service (Uvicorn, Python 3.12)                         │
│  [CORE] PostgreSQL 16+ (Asyncpg, UUID, JSONB, Pgcrypto)                     │
│  [CORE] Redis 7+ (Rate Limiting, Revocation, Cache Invalidation, PubSub)    │
│  [CORE] Next.js 14+ Web Application (Node.js 20)                            │
│  [EDGE] Nginx / Caddy Reverse Proxy & TLS Termination                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component-by-Component Infrastructure Matrix

| Component | Required? | Why (Codebase Usage) | Configuration Parameter | Status |
|---|---|---|---|---|
| **PostgreSQL 16+** | **YES (Mandatory)** | Primary multi-tenant relational data store for all 9 domains, user profiles, audit ledgers, and transactions. | `DATABASE_URL=postgresql+asyncpg://...`<br>`DATABASE_URL_SYNC=postgresql://...` | **VERIFIED** |
| **Redis 7+** | **YES (Mandatory)** | Enforces authentication rate limits (`send_otp`, `login`), token revocation blacklist, and real-time shopping list sync. | `REDIS_URL=redis://localhost:6379/0` | **VERIFIED** |
| **FastAPI Backend** | **YES (Mandatory)** | Core API gateway, domain controllers, RBAC enforcement, dynamic projections, and OpenAPI specs. | `PORT=8000`<br>`ENVIRONMENT=production`<br>`JWT_SECRET_KEY=...` | **VERIFIED** |
| **Next.js Web Client** | **YES (Mandatory)** | Primary desktop/tablet web interface for household management. | `PORT=3000`<br>`NEXT_PUBLIC_API_BASE_URL=...` | **VERIFIED** |
| **Nginx Reverse Proxy** | **YES (Production)** | Edge routing, SSL/TLS termination, HTTP/2, security response headers (`HSTS`, `X-Frame-Options`). | `infrastructure/docker/nginx.conf` | **VERIFIED** |
| **SMS / OTP Gateway** | **YES (Production)** | Delivering 6-digit OTP codes to real mobile phones during registration and login. | SMS Provider Webhook / API credentials | **REQUIRES PRODUCTION CONFIGURATION** |
| **Background Workers** | **NO** | Not required for MVP pilot. Temporal projections and recurrence calculations are executed synchronously on-request. | None | **NOT REQUIRED FOR MVP** |
| **Scheduled Jobs (Cron)**| **YES (Host Level)**| Daily `pg_dump` database backup snapshot with 14-day retention. | Host crontab (`scripts/backup_db.sh`) | **VERIFIED** |
| **Object Storage (S3)** | **NO (Optional)** | Receipts and avatars are stored as URL references in MVP. Object storage integration is deferred to Phase 9. | `STORAGE_ENDPOINT` (Optional) | **NOT REQUIRED FOR MVP** |
| **Push Notifications** | **NO** | In-app Attention Center and Unified Today Agenda handle all domestic coordination for the pilot cohort. | None | **NOT REQUIRED FOR MVP** |
| **Email SMTP Server** | **NO (Optional)** | Household invites support direct token links. SMTP is optional for pilot. | `SMTP_HOST` (Optional) | **OPTIONAL** |

---

## 3. Recommended Pilot Staging Infrastructure Profile

```yaml
Virtual Machine:
  OS: Ubuntu 22.04 LTS
  vCPU: 2 Cores
  RAM: 4 GB
  Storage: 40 GB SSD (NVMe preferred)

Managed Services / Containers:
  - PostgreSQL 16
  - Redis 7
  - Docker & Docker Compose v2
  - Nginx / Certbot (Let's Encrypt SSL)
```
